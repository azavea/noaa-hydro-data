#!/usr/bin/env python
# coding: utf-8

# # Benchmark Zarr vs. Parquet reach queries

import os
import timeit

import xarray as xr
import fsspec
import dask.dataframe as dd
from scipy import stats
import numpy as np


# These reach ids are within a HUC around Cobb's Creek in West Philly.
avail_reach_ids = [4495680, 4495656, 4494480, 4489136, 4489138, 4496602]

# Set these to the location of the Zarr and Parquet data samples.
zarr_path = 's3://research-lf-dev/noaa/reformat-sample/streamflow-zarr/'
parq_path = 's3://research-lf-dev/noaa/reformat-sample/streamflow-parquet/'

# Set this to location of AWS credentials file if it's not in the default place. This is useful 
# if running on MSPC. In that case, just put this in the root directory of the JupyterHub file explorer.
# os.environ['AWS_SHARED_CREDENTIALS_FILE'] = './config'

# Number of repeats to use for benchmarking.
repeat = 20


def get_zarr_streamflow():
    ds = xr.open_zarr(fsspec.get_mapper(zarr_path, anon=False, requester_pays=True))
    sub_ds = ds.sel(feature_id=avail_reach_ids)
    return sub_ds.streamflow.values

def get_parq_streamflow():
    df = dd.read_parquet(parq_path)
    sub_df = df['streamflow'].loc[avail_reach_ids].compute()


zarr_times = timeit.repeat(get_zarr_streamflow, number=1, repeat=repeat)
parq_times = timeit.repeat(get_parq_streamflow, number=1, repeat=repeat)


zarr_mean = np.array(zarr_times).mean()
parq_mean = np.array(parq_times).mean()

print(f'Querying Zarr takes {zarr_mean / parq_mean:.2f}x longer than Parquet.')




