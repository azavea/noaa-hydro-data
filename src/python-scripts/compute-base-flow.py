import logging

import dask
import dask_gateway
import numpy as np
import pandas as pd
import xarray as xr


logger = logging.getLogger("DaskWorkflow")

gw = dask_gateway.Gateway(auth="jupyterhub")
logger.warning(f"Using auth of type {type(gw.auth)}")

try:
    opts = gw.cluster_options()
    opts.worker_memory = int(os.environ['DASK_OPTS__WORKER_MEMORY'])
    opts.worker_cores = int(os.environ['DASK_OPTS__WORKER_CORES'])
    opts.scheduler_memory = int(os.environ['DASK_OPTS__SCHEDULER_MEMORY'])
    opts.scheduler_cores = int(os.environ['DASK_OPTS__SCHEDULER_CORES'])
    cluster = gw.new_cluster(opts)
    cluster.scale(int(os.environ['DASK_OPTS__N_WORKERS']))
    client = cluster.get_client()

    logger.warning(f"Client dashboard: {client.dashboard_link}")

    with dask.config.set(**{'array.slicing.split_large_chunks': False}):
        nwm_uri = 's3://noaa-nwm-retrospective-2-1-zarr-pds/chrtout.zarr'
        ds = xr.open_zarr(nwm_uri)
        recent = ds.where(ds['time'] >= np.datetime64('2010-01-01'), drop=True)
        weekly_avg = recent.streamflow.groupby('time.week').mean().rename('mean')
        weekly_std = recent.streamflow.groupby('time.week').std().rename('std')
        base_flow = xr.merge([weekly_avg, weekly_std])

        base_flow.to_zarr('s3://azavea-noaa-hydro-data-public/nwm-base-flow.zarr', mode='w')
finally:
    gw.stop_cluster(client.cluster.name)
