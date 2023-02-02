import logging
from os.path import basename, join
import os
import shutil
from os import makedirs

import dask
import dask_gateway
import xarray as xr
import fsspec
from rechunker import rechunk
import zarr


logger = logging.getLogger("RechunkWorkflow")

def remove_chunks_encoding(ds):
    for var in list(ds.keys()) + list(ds.coords):
        if 'chunks' in ds[var].encoding:
            del ds[var].encoding['chunks']
    return ds


def _rechunk(src_ds, target_chunks, output_uri, tmp_uri):
    # Putting in a safety factor for memory use; see https://github.com/pangeo-data/rechunker/issues/100#issue-1015598253
    max_mem = f"{int(os.environ['DASK_OPTS__WORKER_MEMORY']) * 3 // 4}GB"
    logger.warning(f"Setting max_mem to {max_mem}")

    # Note, if you get a ContainsArrayError, you probably need to delete temp_store and target_store first.
    # See https://github.com/pangeo-data/rechunker/issues/78

    targ_store = fsspec.get_mapper(output_uri)
    temp_store = fsspec.get_mapper(tmp_uri)
    rechunk_plan = rechunk(src_ds, target_chunks, max_mem, targ_store, temp_store=temp_store)
    rechunk_plan.execute()

def client_code():
    src_uri = 's3://noaa-nwm-retrospective-2-1-zarr-pds/chrtout.zarr'
    with dask.config.set(**{'array.slicing.split_large_chunks': True}):
        nwm_uri = 's3://noaa-nwm-retrospective-2-1-zarr-pds/chrtout.zarr'
        ds = remove_chunks_encoding(
            xr.open_zarr(src_uri).chunk({'time': 672, 'feature_id': 30000})
        )
        target_chunks = {'time': 30000, 'feature_id': 672}
        _rechunk(
            ds,
            target_chunks,
            's3://azavea-noaa-hydro-data/experiments/jp/rechunk/output.zarr',
            tmp_uri='s3://azavea-noaa-hydro-data/experiments/jp/rechunk/tmp.zarr'
        )
        zarr.convenience.consolidate_metadata(
            's3://azavea-noaa-hydro-data/experiments/jp/rechunk/output.zarr'
        )


def main():
    gw = dask_gateway.Gateway()
    cluster_name = None
    logger.warning(f"Using auth type {type(gw.auth)}")

    try:
        opts = gw.cluster_options()
        opts.worker_memory = int(os.environ['DASK_OPTS__WORKER_MEMORY'])
        opts.worker_cores = int(os.environ['DASK_OPTS__WORKER_CORES'])
        opts.scheduler_memory = int(os.environ['DASK_OPTS__SCHEDULER_MEMORY'])
        opts.scheduler_cores = int(os.environ['DASK_OPTS__SCHEDULER_CORES'])
        cluster = gw.new_cluster(opts)
        cluster.scale(int(os.environ['DASK_OPTS__N_WORKERS']))
        client = cluster.get_client()
        cluster_name = cluster.name

        logger.warning(f"Client dashboard: {client.dashboard_link}")

        client_code()
    finally:
        if cluster_name is not None:
            gw.stop_cluster(cluster_name)


if __name__ == '__main__':
    main()
