#!/usr/bin/env python
# coding: utf-8

# # Prepare versions of NWM Reanalysis dataset in Zarr format
# 
# * Save a subset of NWM reanalysis covering a single HUC2 for testing purposes. The size is supposed to be not so small that it is trivial, but not so big that things take a really long time to run. 
# * Rechunk this subset so we have versions with rectangular chunks, row chunks, and column chunks.|

# ## Setup

import json
from os.path import basename, join
import os 
import shutil
from os import makedirs

from dask.distributed import Client
from dask_gateway import Gateway
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


# Set various URIs.

# The CHRTOUT data from the NWM Retrospective Zarr 2.1 dataset
# This has "Streamflow values at points associated with flow lines" 
# See https://registry.opendata.aws/nwm-archive/
nwm_uri = 's3://noaa-nwm-retrospective-2-1-zarr-pds/chrtout.zarr'

# URI of JSON file with COMIDS to use for creating subset of NWM. 
# This was produced by save_huc2_comids.ipynb.
comid_uri = 's3://azavea-noaa-hydro-data/noaa/huc2-comids.json'

# This root URI should be updated for each run of this notebook.
out_root_uri = 's3://azavea-noaa-hydro-data/esip-experiments/datasets/reanalysis-chrtout/zarr/lf/07-08-2022a'


nwm_subset_uri = join(out_root_uri, 'nwm-subset.zarr')
rechunk_tmp_uri = join(out_root_uri, 'rechunk-tmp.zarr')
trans_chunk_uri = join(out_root_uri, 'trans-chunk.zarr')


# ## Save subet of NWM

ds = xr.open_zarr(fsspec.get_mapper(nwm_uri, anon=True, requester_pays=True))

comids = get_json(comid_uri)['comids']

avail_comids = list(set(ds.feature_id.values).intersection(set(comids)))
# Need the following line to sort the comids or will get the following warning.
# PerformanceWarning: Slicing with an out-of-order index is generating 736 times more chunks
avail_comids.sort()
print(
    f'There are {len(comids)} reaches in the HUC and {len(avail_comids)} of those are in NWM.')


# time_range = slice('01-01-1990', '01-01-2000')
time_range = slice('01-01-1990', '01-01-2000')


ds.streamflow


sub_ds = ds.sel(time=time_range, feature_id=avail_comids)

# Fails without this block. See https://github.com/pydata/xarray/issues/5219 
def remove_chunks_encoding(ds):
    for var in list(ds.keys()) + list(ds.coords):
        if 'chunks' in ds[var].encoding:
            del ds[var].encoding['chunks']
    return ds

sub_ds = remove_chunks_encoding(sub_ds)
sub_ds


sub_ds.streamflow


# Fails with the following error if chunk(<int>) isn't called.
# ValueError: Zarr requires uniform chunk sizes except for final chunk. Variable named 'streamflow' has incompatible dask chunks: ((48,), (445, 5348, 802, 2192, 3915, 10509, 12946, 3414, 7504, 87, 13247, 6817, 24143, 2, 11164, 1156, 3632, 499, 1518, 1666, 1633, 8, 3, 4965, 3147, 723, 771)). Consider rechunking using `chunk()`.
sub_ds = remove_chunks_encoding(sub_ds.chunk({'time': 672, 'feature_id': 30000}))
# sub_ds = remove_chunks_encoding(sub_ds.chunk(1000))


sub_ds.streamflow


get_ipython().run_cell_magic('time', '', '\nsub_ds.to_zarr(nwm_subset_uri)\n')


saved_ds = xr.open_zarr(nwm_subset_uri)
saved_ds.streamflow


sub_ds.chunks


# ## Save rechunked versions of subset of NWM.

def _rechunk(target_chunks, output_uri):
    max_mem = '2GB'
    rm(rechunk_tmp_uri)
    ds = xr.open_zarr(nwm_subset_uri)

    # Note, if you get a ContainsArrayError, you probably need to delete temp_store and target_store first.
    # See https://github.com/pangeo-data/rechunker/issues/78

    targ_store = fsspec.get_mapper(output_uri)
    temp_store = fsspec.get_mapper(rechunk_tmp_uri)
    rechunk_plan = rechunk(ds, target_chunks, max_mem, targ_store, temp_store=temp_store)
    rechunk_plan.execute()


get_ipython().run_cell_magic('time', '', "\n# Each chunk has dimension that is the transpose of the original chunk size.\ntrans_chunk_uri = join(out_root_uri, 'trans-chunk.zarr')\ntarget_chunks = {'time': 30000, 'feature_id': 672} \n_rechunk(target_chunks, trans_chunk_uri)\n")


rechunked_ds = xr.open_zarr(square_chunk_uri)
rechunked_ds.chunks

