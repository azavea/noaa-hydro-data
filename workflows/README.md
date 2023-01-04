# Argo Workflow Archive

This directory contains a collection of `Workflow` definitions for Argo to do tasks that we may want to repeat.  As we learn Argo better, we might be able to make better use of these resources for more complex tasks.

## Dask task runner
The provided `run-dask-job.yaml` allows for the specification of an HTTP(S) URL to a Python script which will be downloaded and run in a Dask cluster that will be configured to the scale dictated by the other job parameters.

Scripts that wish to use this framework should use the following as the starting point for their code:
```python
import logging
import dask_gateway

logger = logging.getLogger("DaskWorkflow")
gw = dask_gateway.Gateway(auth="jupyterhub")

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

    # Client code goes here
finally:
    gw.stop_cluster(client.cluster.name)
```
