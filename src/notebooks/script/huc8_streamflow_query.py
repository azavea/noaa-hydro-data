#!/usr/bin/env python
# coding: utf-8

# # Benchmark HUC8 Streamflow Aggregation Queries
# 
# This notebook show how to query the NWM reanalysis dataset using HUC8s in various ways, time the queries, and save the results in a CSV.

# # Setup

import json
from os.path import join
import time

import tqdm
import geopandas as gpd
import xarray as xr
import fsspec
import numpy as np
import pyproj
from dask.distributed import Client
import numpy as np
import pandas as pd
import fsspec

get_ipython().run_line_magic('matplotlib', 'inline')

def get_json(uri):
    with fsspec.open(uri) as fd:
        return json.load(fd)

client = Client()


# Set various URIs.

# Location of HUC8 extract JSON files.
huc8_root_uri = 's3://azavea-noaa-hydro-data/noaa/huc8-extracts/transformed/'

# The CHRTOUT data from the NWM Retrospective Zarr 2.1 dataset
# This has "Streamflow values at points associated with flow lines" 
# See https://registry.opendata.aws/nwm-archive/
nwm_uri = 's3://noaa-nwm-retrospective-2-1-zarr-pds/chrtout.zarr'

# URI of CSV with timings for different queries. This URI should be updated each time this notebook is run.
timings_uri = 's3://azavea-noaa-hydro-data/esip-experiments/benchmarks/test-06-27-2021a.csv'


# Get COMIDs for a HUC8 around Philly from a HUC8 extract on S3.
# Each COMID represents a stream reach.
# TODO: run this with multiple HUC8s.
philly_huc8 = '02040202'
huc8_uri = join(huc8_root_uri, f'{philly_huc8}.json')

huc8_dict = get_json(huc8_uri)
comids = huc8_dict['features'][0]['properties']['comids']


# # Query NWM

ds = xr.open_zarr(fsspec.get_mapper(nwm_uri, anon=True, requester_pays=True))
ds


# Apparently, only some of the reach ids in NHDPlus V2 are available in NWM.
# Question: why is that?
avail_comids = list(set(ds.feature_id.values).intersection(set(comids)))
print(
    f'There are {len(comids)} reaches in the HUC and {len(avail_comids)} of those are in NWM.')


# Note that the chunks are rectangular (2D) as opposed to whole rows or whole columns.
ds.streamflow


# Lazily compute the subset of the dataset that contains a certain time range.
# TODO: run this with several time ranges including those with week or years long ranges.
time_range = slice('1980-01-01', '1980-01-03')
sub_ds = ds.sel(feature_id=avail_comids, time=time_range)
sub_ds


def time_func(func, repeats=1):
    """Times the running a function.
    
    Args:
        func: an argumentless function aka a thunk
        repeats: the number of times to repeat execution

    Return:
        a numpy array of length repeats with the runtime in seconds for each execution
    """
    times = []
    for _ in tqdm.tqdm(range(repeats), leave=False, desc='repeat'):
        start_time = time.time()
        func()
        elapsed = time.time() - start_time
        times.append(elapsed)
    return np.array(times)


# The number of times to repeat execution
# TODO: use more repeats
repeats = 1

# A map from query nicknames to functions that execute the query.
query_map = {
    'mean_features_mean_day': (lambda: sub_ds.streamflow.mean(dim='feature_id').groupby('time.dayofyear').mean().values),
    'mean_day': (lambda: sub_ds.streamflow.groupby('time.dayofyear').mean().values),
    'mean_week': (lambda: sub_ds.streamflow.groupby('time.weekofyear').mean().values)
}

# Build a dataframe with a row for each experiment.
query = []
time_mean = []
time_std = []
for qname, qfunc in tqdm.tqdm(query_map.items(), desc='query'):
    times = time_func(qfunc, repeats=repeats)
    query.append(qname)
    time_mean.append(times.mean())
    time_std.append(times.std())
df = pd.DataFrame(data={'query': query, 'time_mean': time_mean, 'time_std': time_std})


nb_reaches = len(avail_s)
nb_days = (pd.to_datetime(time_range.stop) - pd.to_datetime(time_range.start)).days
format = 'zarr'
chunk_sizes = np.array([ds.streamflow.chunks[0][0], ds.streamflow.chunks[1][0]])
time_chunk_sz = chunk_sizes[0]
feature_id_chunk_sz = chunk_sizes[1]

df['nb_reaches'] = nb_reaches
df['nb_days'] = nb_days
df['nb_repeats'] = repeats
df['format'] = format
df['time_chunk_sz'] = time_chunk_sz
df['feature_id_chunk_sz'] = feature_id_chunk_sz


df


df.to_csv(timings_uri)

