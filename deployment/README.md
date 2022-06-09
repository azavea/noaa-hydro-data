# Daskhub Kubernetes Cluster Deployment

This directory contains the needed configurations to create and interact with a Kubernetes cluster hosting a Daskhub instance (Jupyterhub + Dask).  This cluster employs the Karpenter autoscaler to keep resource usage to a minimum, scaling the cluster nodes on demand.

Most Daskhub configurations are borrowed from Pangeo's Daskhub configurations.  Note that the configurations here separately deploy Jupyterhub and Dask-Gateway, due to the official Daskhub Helm chart being slightly behind in its Dask-Gateway version.  We may move to support the official Daskhub Helm chart in the future.

## Basic setup

The deployment process involves the creation of a local docker image, and the creation of infrastructure through Terraform.  The resulting cluster can then be interacted with using Lens and/or `kubectl`.

### Create and run the Docker image

From this directory (`deployment`), run `./scripts/cibuild`.  This will build the Terraform-enabled environment.  `kubectl` and `helm` with also be available in this environment.  This image will create a default user with the same username, UID, and GID as the host environment, to avoid polluting the host filesystem with files of the wrong owner.

> Note that this build process needs more extensive testing to ensure it will work on other hosts.  It has currently only been tested on Linux.

This image should then be entered via
```bash
docker-compose -f docker-compose.yml run terraform
```
Several environment variables from the host system will be imported into this environment, including `AWS_PROFILE`, which should be properly set before running.  The host's `$HOME/.aws` directory will be mounted into the container, as will the `$HOME/.kube` directory.

Note that settings for the Terraform infrastructure will be stored on S3, and the location can be customized with the `NOAA_SETTINGS_S3_PATH` environment variable.  (These settings can be conveniently edited using the `./scripts/edit-tfvars` script from the container environment.)

### Deploy the infrastructure

To create a new cluster, simply issue the following commands from the container environment:
```bash
./scripts/infra plan
./scripts/infra apply
```
Alternatively, one may use `./scripts/cipublish` from the host.

This will take about 20 minutes, but the result will be a new EKS Kubernetes cluster running Karpenter, Jupyterhub, and Dask.  `infra apply` will also export the cluster settings to the `$HOME/.kube/config` file on both the host and container, meaning that the user can run [Lens](https://k8slens.dev/) on their local machine to get a convenient UI for interaction.  `kubectl` is also a viable method of interaction from both the host and container environments.

### Connecting to existing infrastructure

Since a cluster is intended to be shared across users, if you do not need to create a new cluster, you may instead connect to a cluster by executing
```bash
./scripts/infra connect
```
from the docker-compose environment.  Disconnecting from a cluster (removing it from the `.kube/config`) can be accomplished using `./scripts/infra disconnect`.

### Destroying a cluster

When the cluster will not be needed for an extended period, issue `./scripts/infra destroy` from the container environment.  Due to the use of Karpenter, however, resource usage for a k8s cluster should be minimal if not in use.  Be sure to close down Dask and Jupyter resources to allow nodes to spin down.  This can be checked from Lens or `kubectl`.

## Using Dask

Once connected to a running cluster, the process of accessing Daskhub is as follows:

1. Forward port 8000 from the `proxy-########` pod (the hashes will be replaced by a random string) to your local port 8000 (use https).  Accessing `localhost:8000` should direct you to log in to Jupyterhub.

2. Log in.  (At present, only the `jovyan:jupyter` credentials are enabled.)  This should result in access to a Jupyter notebook.

3. Use the following basic code to create a Dask gateway, cluster, and client:
   ```python
   from dask_gateway import Gateway

   gateway = Gateway(
       address="http://traefik-dask-gateway/services/dask-gateway/",
       proxy_address="gateway://traefik-dask-gateway:80",
       auth="jupyterhub"
   )
   cluster = gateway.new_cluster()
   client = cluster.get_client()
   ```
   You should now be able to run Dask jobs.
