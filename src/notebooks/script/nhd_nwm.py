#!/usr/bin/env python
# coding: utf-8

# # Joining NHD + NWM
# 
# This notebook shows how to get a HUC by id, query NHD for all reaches within the HUC, and then query NWM (in Zarr format) to get gridded and reach-based data.
# 
# This assumes that a small sample of the NHDPlus V2 and NHDPlus HR databases (covering the area around Philly) has been loaded into a local database following the README.
# 

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

# Get HUC by id
cursor = get_cursor('nhdplushr')
huc12 = '020402020504'
query = "SELECT wkb_geometry from wbdhu12 WHERE huc12=%s"
cursor.execute(query, [huc12])
huc_geom = shapely.wkb.loads(cursor.fetchone()[0], hex=True)
huc_geom


# Get reaches that that intersect the HUC
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
    reach_geoms.append(shapely.wkb.loads(reach_geom, hex=True))


# Plot the HUC and reaches.
# It's strange that some of the reaches seem to be missing.
df = gpd.GeoDataFrame({'geometry': reach_geoms + [huc_geom]})
df.plot(facecolor="none")


# # Query NWM by reach ids

# Load the CHRTOUT data from the NWM Retrospective Zarr 2.1 dataset
# This has "Streamflow values at points associated with flow lines" 
# See https://registry.opendata.aws/nwm-archive/
nwm_uri = 's3://noaa-nwm-retrospective-2-1-zarr-pds/chrtout.zarr'
ds = xr.open_zarr(fsspec.get_mapper(nwm_uri, anon=True, requester_pays=True))
ds


# Apparently, only some of the reach ids are available in NWM.
avail_reach_ids = list(set(ds.feature_id.values).intersection(set(reach_ids)))
print(
    f'There are {len(reach_ids)} reaches in the HUC and {len(avail_reach_ids)} of those are in NWM.')

# Lazily compute the subset of the dataset that contains the reaches for a single point in time.
sub_ds = ds.sel(feature_id=avail_reach_ids, time='1979-02-01T01:00:00')
sub_ds


get_ipython().run_cell_magic('time', '', '# Actually get the streamflow values.\nsub_ds.streamflow.values\n')


# # Query gridded NWM data

# Load the RTOUT data from the NWM Retrospective Zarr 2.1 dataset
# This has "Ponded water and depth to soil saturation" which is one of the gridded data products.
# See https://registry.opendata.aws/nwm-archive/
nwm_uri = 's3://noaa-nwm-retrospective-2-1-zarr-pds/rtout.zarr'
ds = xr.open_zarr(fsspec.get_mapper(nwm_uri, anon=True, requester_pays=True))
ds


# Get bounding box around HUC to use for querying.
from_crs = pyproj.CRS('EPSG:4326')
to_crs = pyproj.CRS(ds.proj4)
project = pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True).transform
trans_huc_box = shapely.ops.transform(project, shapely.geometry.box(*huc_geom.bounds))
trans_huc_box.bounds


# Query the area over the HUC for a specific day.
minx, miny, maxx, maxy = trans_huc_box.bounds
sub_ds = ds.sel(time='1979-02-01', x=slice(minx, maxx), y=slice(miny, maxy))
sub_ds


get_ipython().run_cell_magic('time', '', '\n# Get actual values.\nsub_ds.zwattablrt.values\n')

