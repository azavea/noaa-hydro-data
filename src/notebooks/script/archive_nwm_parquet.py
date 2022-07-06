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
import dask.dataframe as ddf


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
data_type = 'channel_rt'
download_hour_files = False

if download_hour_files:
    for cycle_runtime in [1, 2]:
        for forecast_hour in [1, 2]:
            nwm_uri = get_nwm_uri(date, data_type, cycle_runtime, forecast_hour)
            nwm_path = join(tmp_dir, basename(nwm_uri))
            print(f'Downloading {nwm_uri}')
            request.urlretrieve(nwm_uri, nwm_path)


sample_path = join(tmp_dir, 'nwm.t01z.short_range.channel_rt.f001.conus.nc')
ds = xr.open_dataset(sample_path)
ds


chunks = {'time': 1, 'feature_id': 100_000}
out_path = join(archive_dir, f'{data_type}.parquet')
out_index_path = join(archive_dir, f'{data_type}-index.parquet')

# Append forecast_hour to the temporary file.
# Don't append during the first iteration.
append = False
for cycle_runtime in tqdm([1, 2]):
    for forecast_hour in tqdm([1, 2]):
        nwm_uri = get_nwm_uri(date, data_type, cycle_runtime, forecast_hour)
        nwm_path = join(tmp_dir, basename(nwm_uri))

        with xr.open_dataset(nwm_path, chunks=chunks) as ds:
            ds = ds.drop('crs')
            # Replace with offset hour instead of absolute time.
            ds = ds.assign_coords(time=np.array([forecast_hour]))
            df = ds.to_dask_dataframe()
                
            # Note Parquet version of file is much larger than NetCDF (200 mb vs. 40 mb)
            df.to_parquet(out_path, append=append, ignore_divisions=True)

            df = df.set_index('feature_id')
            df.to_parquet(out_index_path, append=append, ignore_divisions=True)

            append = True


# # Test reading under various conditions.
# 
# It takes about 25 secs for the first execution with or without an index.

# Test reading the output without an index.
df = ddf.read_parquet(out_path)
df = df[df['feature_id'] == 101]
df.compute()


# Test reading the output with an index.
df = ddf.read_parquet(out_index_path)
df = df.loc[101]
df.compute()




