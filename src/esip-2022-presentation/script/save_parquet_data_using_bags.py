#!/usr/bin/env python
# coding: utf-8

# # Save NWM to Parquet using Bags in parallel 

import json
from os.path import basename, join
import os 
import shutil
from os import makedirs

import dask.bag as db
import dask.dataframe as dd
from dask.distributed import Client
import xarray as xr
import fsspec
from rechunker import rechunk
import s3fs
import fsspec

get_ipython().run_line_magic('matplotlib', 'inline')

def get_json(uri):
    with fsspec.open(uri) as fd:
        return json.load(fd)


# Connect to existing cluster using cluster.name

# This constant needs to be set!
cluster_name = ''
gateway = Gateway()
cluster = gateway.connect(cluster_name)
client = cluster.get_client()


# one year subset of data
zarr_uri = 's3://azavea-noaa-hydro-data/esip-experiments/datasets/reanalysis-chrtout/zarr/07-06-2022b/nwm-subset.zarr/'
out_root_uri = 's3://azavea-noaa-hydro-data/esip-experiments/datasets/reanalysis-chrtout/parquet/lf/07-11-2022a'

zarr_ds = xr.open_zarr(zarr_uri)
zarr_ds


def save_parquet_segment(bounds):
    start_ind, end_ind = bounds
    sub_ds = zarr_ds.sel(feature_id=zarr_ds.feature_id[start_ind:end_ind])
    # Using `to_dask_dataframe` works, but seems to get bottlenecked running almost everything on a single worker.
    # Using `to_dataframe` runs much faster, but fails when mapping > 32 items in the cells below.
    df = sub_ds.to_dask_dataframe()
    df.to_parquet(join(out_root_uri, f'nwm-{start_ind}-{end_ind}.parquet'), engine='pyarrow')
    # TODO: delete stuff explicitly


features_per_store = 2000
feature_bounds = [
    (start_ind, min(start_ind + features_per_store, zarr_ds.feature_id.shape[0]))
    for start_ind in range(0, zarr_ds.feature_id.shape[0], features_per_store)]


b = db.from_sequence(feature_bounds, npartitions=len(feature_bounds))
b = b.map(save_parquet_segment)
results_bag = b.compute()


ddf = dd.read_parquet(out_root_uri)


ddf

