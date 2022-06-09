resource "random_id" "daskhub_token" {
  byte_length = 32
}

# resource "helm_release" "daskhub" {
#   depends_on       = [
#     module.eks.kubeconfig,
#     kubectl_manifest.karpenter_provisioner
#   ]
#   namespace        = "daskhub"
#   create_namespace = true

#   name       = "dhub"
#   repository = "https://helm.dask.org/"
#   chart      = "dask/daskhub"
#   version    = "2022.5.0"

#   values = [
#     "${file("yaml/daskhub-values.yaml")}"
#   ]

#   set {
#     name  = "jupyterhub.hub.services.dask-gateway.apiToken"
#     value = random_id.daskhub_token.hex
#   }

#   set {
#     name  = "jupyterhub.proxy.secretToken"
#     value = random_id.daskhub_token.hex
#   }

#   set {
#     name  = "dask-gateway.gateway.auth.jupyterhub.apiToken"
#     value = random_id.daskhub_token.hex
#   }

#   set {
#     name = "jupyterhub.hub.singleuser.startTimeout"
#     value = 300
#   }
# }

resource "helm_release" "jupyterhub" {
  depends_on       = [
    module.eks.kubeconfig,
    kubectl_manifest.karpenter_provisioner
  ]
  namespace        = "daskhub"
  create_namespace = true

  name       = "jupyterhub"
  repository = "https://jupyterhub.github.io/helm-chart/"
  chart      = "jupyterhub"
  version    = "1.2.0"

  values = [
    "${file("yaml/jupyterhub-values.yaml")}"
  ]

  set {
    name  = "hub.services.dask-gateway.apiToken"
    value = random_id.daskhub_token.hex
  }

  set {
    name  = "proxy.secretToken"
    value = random_id.daskhub_token.hex
  }

  set {
    name = "singleuser.startTimeout"
    value = 300
  }
}

resource "helm_release" "dask_gateway" {
  depends_on       = [
    module.eks.kubeconfig,
    kubectl_manifest.karpenter_provisioner,
    helm_release.jupyterhub
  ]
  namespace        = "daskhub"
  create_namespace = true

  name       = "dask-gateway"
  repository = "https://helm.dask.org/"
  chart      = "dask-gateway"
  version    = "2022.4.0"

  values = [
    "${file("yaml/dask-gateway-values.yaml")}"
  ]

  set {
    name  = "gateway.auth.jupyterhub.apiToken"
    value = random_id.daskhub_token.hex
  }
}
