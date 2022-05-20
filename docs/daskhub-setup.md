# Setup Instructions

This describes how to install [DaskHub](https://github.com/dask/helm-chart/tree/main/daskhub) which combines [JupyterHub](https://zero-to-jupyterhub.readthedocs.io/en/latest/) (a multi-user Jupyter notebook server) with [Dask Gateway](https://gateway.dask.org/install-kube.html) on Kubernetes.

## Install DaskHub locally

* Install `minikube` and `kubectl` and `helm`.
* The released version of the DaskHub Helm chart does not work, so need to install from source.
* Checkout these two repos locally: https://github.com/dask/helm-chart (commit 0b2c26) and https://github.com/dask/dask-gateway (commit 0a69d3d)
* In `helm-chart/daskhub`, edit the following files to have the following content:
  * `Chart.yaml`:
    ```
    - name: dask-gateway
        version: "0.9.0"
        repository: 'file:///Users/lewfish/projects/dask-gateway/resources/helm/dask-gateway/'
    ```
  * `values.yaml`
    ```
    singleuser:
        image:
        name: pangeo/base-notebook  # Image to use for singleuser environment. Must include dask-gateway.
        tag: 2021.12.02
    ```
  *  `dev-values.yaml` (this stuff comes from https://github.com/dask/helm-chart/blob/main/daskhub/README.md#matching-the-user-environment)
    ```
    jupyterhub:
     singleuser:
       extraEnv:
         DASK_GATEWAY__CLUSTER__OPTIONS__IMAGE: '{JUPYTER_IMAGE_SPEC}'
    
    dask-gateway:
      traefik:
        service:
          type: "LoadBalancer"
    
      gateway:
        extraConfig:
          optionHandler: |
            from dask_gateway_server.options import Options, Integer, Float, String
            def option_handler(options):
                if ":" not in options.image:
                    raise ValueError("When specifying an image you must also provide a tag")
                return {
                    "image": options.image,
                }
            c.Backend.cluster_options = Options(
                String("image", default="pangeo/base-notebook:2020.07.28", label="Image"),
                handler=option_handler,
            )
   ```
  * Make a new file `secrets.yaml` with the following contents. If you want to deploy this on EKS later, you will want to fill in the token fields with a value generated by `openssl rand -hex 32`.
    ```
      jupyterhub:
        hub:
          services:
            dask-gateway:
              apiToken: "foo000111"
        proxy:
          secretToken: "foo000111"
      
      dask-gateway:
        gateway:
          auth:
            jupyterhub:
              apiToken: "foo000111"
   ```
* In `helm-chart/daskhub`, run `helm dependency build` and then `helm install local-daskhub ./ --values ./values.yaml --values ./dev-values.yaml --values ./secrets.yaml`.
* Using the Lens app, you should be able to see things starting and running. In the Services view, click on `proxy-public`, and then navigate to Connection -> Ports -> Forward -> Start. (You may need to click Stop/Remove first). This should open the JupyterHub page in a browser.
* Login using `dask` for the username and password.
* You may want to run `helm uninstall local-daskhub` to reset things.

## Notebook Configuration

Make a new Jupyter notebook and run the following code.

```
from dask_gateway import Gateway, GatewayCluster
cluster = GatewayCluster()
gateway = Gateway()
gateway.list_clusters()

client = cluster.get_client()
client
```