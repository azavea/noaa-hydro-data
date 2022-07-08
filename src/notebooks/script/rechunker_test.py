#!/usr/bin/env python
# coding: utf-8

# # Test Rechunker on NWM
# 
# Save a small piece of NWM and then rechunk it using the `rechunker` library.

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
from rechunker import rechunk

get_ipython().run_line_magic('matplotlib', 'inline')


# ## First, save a sample of NWM.

# Load the CHRTOUT data from the NWM Retrospective Zarr 2.1 dataset
# This has "Streamflow values at points associated with flow lines" 
# See https://registry.opendata.aws/nwm-archive/
nwm_uri = 's3://noaa-nwm-retrospective-2-1-zarr-pds/chrtout.zarr'
ds = xr.open_zarr(fsspec.get_mapper(nwm_uri, anon=True, requester_pays=True))
ds


ds.streamflow.sel(time='05-20-2022:05-22-2022')


root_dir = '/opt/data/noaa/rechunker-test'
if os.path.isdir(root_dir):
    shutil.rmtree(root_dir)
makedirs(root_dir)

nwm_path = join(root_dir, 'nwm-sample')


ds.streamflow


sub_ds = ds.isel(time=slice(0, 5000), feature_id=slice(0, 5000))


sub_ds.streamflow


sub_ds.to_zarr(nwm_path)


target_chunks = {'feature_id': 300, 'time': 300}
# TODO what is max_mem for?
max_mem = '20MB'

target_store = join(root_dir, 'nwm-target.zarr')
temp_store = join(root_dir, 'nwm-temp.zarr')

# Note, if you get a ContainsArrayError, you probably need to delete temp_store and target_store first.
# See https://github.com/pangeo-data/rechunker/issues/78
rechunk_plan = rechunk(sub_ds, target_chunks, max_mem, target_store, temp_store=temp_store)
rechunk_plan


rechunk_plan.execute()


rechunked_ds = xr.open_zarr(target_store)
rechunked_ds
# TODO why warning about consolidated metadata?


rechunked_ds.streamflow

