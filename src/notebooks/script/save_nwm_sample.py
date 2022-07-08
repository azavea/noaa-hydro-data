#!/usr/bin/env python
# coding: utf-8

# # Save subset of NWM in Zarr and Parquet format
# 
# This saves a subset of the NWM CHRTOUT dataset in Zarr and Parquet format. The data is chunked along the `feature_id` dimension in order to optimized for querying a subset of the reaches. This can be used to support benchmarks that compare the speed of queries using this different formats.

# # Setup

import json
from os.path import join
from os import makedirs
import os
import shutil

import dask.dataframe as dd
import psycopg2
import shapely
import shapely.wkt
import geopandas as gpd
import xarray as xr
import fsspec
import numpy as np
import pyproj
import pandas as pd

get_ipython().run_line_magic('matplotlib', 'inline')


def get_cursor(database):
    connection = psycopg2.connect(host="database", database=database,user="postgres", password="password")
    cursor = connection.cursor()
    return cursor


# # Make sample of dataset
# 
# To speed up downstream processes, we create a small subset of NWM CHRTOUT that only covers the reaches in a portion of the country that is around Philly.

# get all reaches in local sample of nhdplusv2 
cursor = get_cursor('nhdplusv2')
query = f'''
    SELECT comid from nhdflowline
    '''
cursor.execute(query)
reach_ids = [int(x[0]) for x in cursor]
print(f'There are {len(reach_ids)} reach ids in the local copy of NHDPlusV2.')


# Load the CHRTOUT data from the NWM Retrospective Zarr 2.1 dataset
# This has "Streamflow values at points associated with flow lines" 
# See https://registry.opendata.aws/nwm-archive/
nwm_uri = 's3://noaa-nwm-retrospective-2-1-zarr-pds/chrtout.zarr'
ds = xr.open_zarr(fsspec.get_mapper(nwm_uri, anon=True, requester_pays=True))
ds


# Get a sample of the dataset that covers the reach_ids in the local DB, and a single day.
# If a whole month is used, the notebook will die.
avail_reach_ids = list(set(ds.feature_id.values).intersection(set(reach_ids)))
print(
    f'There are {len(reach_ids)} reaches in the DB and {len(avail_reach_ids)} of those are in NWM.')
avail_reach_ids = [int(x) for x in avail_reach_ids]
avail_reach_ids.sort()

sub_ds = ds.sel(feature_id=avail_reach_ids, time='1979-02-01')

orig_gb = (4 * ds.streamflow.size) / (10 ** 9)
sub_gb = (4 * sub_ds.streamflow.size) / (10 ** 9)

print(f'Original dataset is {orig_gb:.2f} gb')
print(f'Sample dataset is {sub_gb:.2f} gb')

sub_ds


# # Save sample of dataset in Zarr and Parquet format

reformat_dir = '/opt/data/noaa/reformat-sample/'
parq_path = join(reformat_dir, 'streamflow-parquet')
zarr_path = join(reformat_dir, 'streamflow-zarr')


get_ipython().run_cell_magic('time', '', "\n# save sample in parquet format\n# why does it take 8 mins??\nif os.path.isdir(parq_path):\n    shutil.rmtree(parq_path)\nmakedirs(parq_path)\n\n# Why do I need to call unify_chunks?\ndf = sub_ds.unify_chunks().to_dask_dataframe()\ndf = df.set_index('feature_id')\ndf.to_parquet(parq_path)\n")


get_ipython().run_cell_magic('time', '', '\n# save sample in zarr format\nif os.path.isdir(zarr_path):\n    shutil.rmtree(zarr_path)\nmakedirs(zarr_path)\n# TODO not sure why I need the next line or set safe_chunks=False\nsub_ds = sub_ds.unify_chunks().chunk()\nsub_ds.to_zarr(zarr_path, safe_chunks=False)\n')


# It's chunked across the feature_ids.
sub_ds.unify_chunks().chunksizes




