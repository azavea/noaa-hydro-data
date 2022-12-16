import logging

import dask
import dask_gateway
import numpy as np
import pandas as pd
import xarray as xr


logger = logging.getLogger("DaskWorkflow")

try:
    gw = dask_gateway.Gateway(auth="jupyterhub")
    logger.warning(f"Using auth of type {type(gw.auth)}")

    opts = gw.cluster_options()
    opts.worker_memory = 10
    if gw.list_clusters() == []:
        cluster = gw.new_cluster(opts)
        cluster.scale(16)
    else:
        cluster = dask_gateway.GatewayCluster.from_name(gw.list_clusters()[0].name)

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
