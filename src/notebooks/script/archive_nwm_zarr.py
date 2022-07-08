#!/usr/bin/env python
# coding: utf-8

# # Demo of archiving NWM predictions 
# 
# This notebook demonstrates how to download NWM predictions and append them to Zarr files, and could form the basis of an NWM archive service. Zarr works well for gridded data, but Parquet seems preferable for point-based data. However, it is unclear if we can append to Parquet. A future iteration of this may investigate how to append to Parquet.

from os.path import join, exists, basename
import tempfile
from urllib import request
from os import makedirs
import os
import shutil

from tqdm import tqdm
import numpy as np
import xarray as xr
import pandas as pd


out_dir = '/opt/data/noaa/nwm-preds'
archive_dir = join(out_dir, 'archive')
tmp_dir = join(out_dir, 'tmp')
makedirs(archive_dir, exist_ok=True)
makedirs(tmp_dir, exist_ok=True)


from dask.distributed import Client
client = Client(n_workers=8)


def get_nwm_uri(date, data_type, cycle_runtime, forecast_hour):
    cycle_runtime = f'{cycle_runtime:02}'
    forecast_hour = f'{forecast_hour:03}'
    return (
        f'https://nomads.ncep.noaa.gov/pub/data/nccf/com/nwm/prod/nwm.{date}/short_range/'
        f'nwm.t{cycle_runtime}z.short_range.{data_type}.f{forecast_hour}.conus.nc')


# ## Download a subset of NWM predictions for today
# 
# For each day, there is a prediction file for each point within a 2D space with the following dimensions:
# * `cycle_runtime`: a time when the predictions were generated; values are in [0-23]
# * `forecast_hour`: how far into the future the predictions are, indexed by the hour offset from the `cycle_runtime`; values are in [1-18].
# 
# Here we download a 2x2 grid for testing purposes.

ts = pd.Timestamp.utcnow()
date = ts.strftime("%Y%m%d")
# The set of data_types includes ['channel_rt', 'land', 'reservoir', 'terrain_rt']
data_type = 'terrain_rt'
download_hour_files = False

if download_hour_files:
    for cycle_runtime in [1, 2]:
        for forecast_hour in [1, 2]:
            nwm_uri = get_nwm_uri(date, data_type, cycle_runtime, forecast_hour)
            nwm_path = join(tmp_dir, basename(nwm_uri))
            print(f'Downloading {nwm_uri}')
            request.urlretrieve(nwm_uri, nwm_path)


# To create the archive file, we need to append predictions along the two dimensions, which isn't possible using Zarr. So, our workaround is to create a temporary Zarr file for a single `cycle_runtime`, and append along the `forecast_hour` dimension. Once we have the full temporary Zarr file for a single `cycle_runtime`, we can append it to the main archive Zarr file along the `cycle_runtime` dimension.

out_path = join(archive_dir, f'{data_type}.zarr')
for cycle_runtime in tqdm([1, 2]):
    cycle_tmp_path = join(tmp_dir, f'cycle-tmp-{cycle_runtime}.zarr')
    
    # Append forecast_hour to the temporary file.
    for forecast_hour in tqdm([1, 2]):
        nwm_uri = get_nwm_uri(date, data_type, cycle_runtime, forecast_hour)
        nwm_path = join(tmp_dir, basename(nwm_uri))

        with xr.open_dataset(nwm_path, chunks={'time': 1, 'y': 1000}) as ds:
            ds = ds.drop('crs')
            # Replace with offset hour instead of absolute time.
            ds = ds.assign_coords(time=np.array([forecast_hour]))
            append_dim = 'time' if forecast_hour != 1 else None
            ds.to_zarr(cycle_tmp_path, append_dim=append_dim)
        
    # Append the temporary file along the cycle_runtime dimension, and then delete the temp file.
    # Need to use chunks argument to use Dask arrays which allow streaming IO.
    with xr.open_dataset(cycle_tmp_path, chunks={'time': 1, 'y': 1000}) as ds:
        ds = ds.assign_coords(reference_time=np.array([cycle_runtime]))
        ds['zwattablrt'] = ds.zwattablrt.expand_dims('reference_time')
        ds['sfcheadsubrt'] = ds.sfcheadsubrt.expand_dims('reference_time')
        append_dim = 'reference_time' if cycle_runtime != 1 else None
        ds.to_zarr(out_path, append_dim=append_dim)
        
    shutil.rmtree(cycle_tmp_path)


ds = xr.open_dataset(out_path, chunks={'time': 1, 'y': 1000})
ds


ds.zwattablrt


# can we reorder the dimensions and still append?
# point-based dataset 
# save in parquet

