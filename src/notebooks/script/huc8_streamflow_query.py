#!/usr/bin/env python
# coding: utf-8

# # HUC8 Streamflow Aggregation Query
# 
# This notebook shows how to get a HUC8 by id, query NHD for all reaches within the HUC, and then query the NWM reanalysis dataset to get aggregated streamflow values.
# 
# Note: this is a work in progress. See TODOs.

# # Setup

import json

import psycopg2
import shapely
import shapely.wkt
import geopandas as gpd
import xarray as xr
import fsspec
import numpy as np
import pyproj

get_ipython().run_line_magic('matplotlib', 'inline')


def get_cursor(database):
    connection = psycopg2.connect(host="database", database=database,user="postgres", password="password")
    cursor = connection.cursor()
    return cursor


# # Use NHD to get a HUC and reaches around Cobb's Creek in West Philly

# TODO instead of using database, use HUC8 extracts on S3 to do query for a few HUC8s.

# Get HUC by id

# Use NHDPlus HR because it has HUC boundaries
cursor = get_cursor('nhdplushr')
huc12 = '020402020504'
query = "SELECT wkb_geometry from wbdhu12 WHERE huc12=%s"
cursor.execute(query, [huc12])
huc_geom = shapely.wkb.loads(cursor.fetchone()[0].tobytes())
huc_geom


# Get reaches that intersect the HUC
# Note that only NHDv2 (and apparently not NHDPlus HR) has the ComId field which is 
# used to index reaches in NWM as the feature_id.
cursor = get_cursor('nhdplusv2')
query = f'''
    SELECT comid, wkb_geometry from nhdflowline WHERE ST_Intersects(
        ST_GeomFromWKB(wkb_geometry, 4326), ST_GeomFromGeoJSON(%s))
    '''

huc_geom_str = json.dumps(shapely.geometry.mapping(huc_geom))
cursor.execute(query, [huc_geom_str])
reach_geoms = []
reach_ids = []
for reach_id, reach_geom in cursor:
    reach_ids.append(reach_id)
    reach_geoms.append(shapely.wkb.loads(reach_geom.tobytes()))


# Plot the HUC and reaches.
# It's strange that some of the reach segments seem to be missing.
# Question: why is that?
df = gpd.GeoDataFrame({'geometry': reach_geoms + [huc_geom]})
df.plot(facecolor="none")


# # Query NWM by reach ids

# Load the CHRTOUT data from the NWM Retrospective Zarr 2.1 dataset
# This has "Streamflow values at points associated with flow lines" 
# See https://registry.opendata.aws/nwm-archive/
nwm_uri = 's3://noaa-nwm-retrospective-2-1-zarr-pds/chrtout.zarr'
ds = xr.open_zarr(fsspec.get_mapper(nwm_uri, anon=True, requester_pays=True))
ds


# Note that the chunks are 2D as opposed to whole rows or whole columns.
ds.streamflow


# Queries can be seen as lying on a spectrum that ranges from "a single time step and all features" to "all time steps and one feature."
# This is to get an idea how the current chunking pattern supports these extremes.
shape = np.array(ds.streamflow.shape)
chunk_sizes = np.array([ds.streamflow.chunks[0][0], ds.streamflow.chunks[1][0]])
nb_chunks = shape // chunk_sizes
gb_per_chunk = (chunk_sizes.prod() * 8) / (10 ** 9)

print(f'The number of chunks for each dimension: {nb_chunks}')
print(f'For a whole time series and single feature: {nb_chunks[0]} chunks, and {nb_chunks[0] * gb_per_chunk :.1f} GB')
print(f'For a single time step and all features: {nb_chunks[1]} chunks, and {nb_chunks[1] * gb_per_chunk :.1f} GB')


# Apparently, only some of the reach ids in NHDPlus V2 are available in NWM.
# Question: why is that?
avail_reach_ids = list(set(ds.feature_id.values).intersection(set(reach_ids)))
print(
    f'There are {len(reach_ids)} reaches in the HUC and {len(avail_reach_ids)} of those are in NWM.')


# Perform the query: lazily compute the subset of the dataset that contains the reaches for a time range.
sub_ds = ds.sel(feature_id=avail_reach_ids, time=slice('1979-02-01', '1979-02-15'))
sub_ds


get_ipython().run_cell_magic('time', '', '\n# Actually get the streamflow values.\nvals = sub_ds.streamflow.values\nvals.shape\n')


get_ipython().run_cell_magic('time', '', "\n# Compute mean for each day.\nvals = sub_ds.streamflow.groupby('time.dayofyear').mean().values\nvals.shape\n")

