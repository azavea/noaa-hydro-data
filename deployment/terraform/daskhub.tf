resource "random_id" "daskhub_token" {
  byte_length = 32
}

### Saving this as a reminder that there is a "proper" Daskhub helm chart that
### we should endeavor to support directly one day
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

  # All static settings belong in the following YAML
  values = [
    "${file("yaml/jupyterhub-values.yaml")}"
  ]

  # Settings which depend on Terraform resources should be set separately
  set {
    name  = "hub.services.dask-gateway.apiToken"
    value = random_id.daskhub_token.hex
  }

  set {
    name  = "proxy.secretToken"
    value = random_id.daskhub_token.hex
  }

  set {
    name = "proxy.https.hosts[0]"
    value = "jupyter.${var.r53_public_hosted_zone}"
  }

  set {
    name = "proxy.https.letsencrypt.contactEmail"
    value = var.letsencrypt_contact_email
  }

  set {
    name = "hub.extraEnv.OAUTH_CALLBACK_URL"
    value = "https://jupyter.${var.r53_public_hosted_zone}/hub/oauth_callback"
  }

  set {
    name = "hub.extraEnv.OAUTH2_AUTHORIZE_URL"
    value = "https://${local.cognito_domain}/oauth2/authorize"
  }

  set {
    name = "hub.extraEnv.OAUTH2_TOKEN_URL"
    value = "https://${local.cognito_domain}/oauth2/token"
  }

  set {
    name = "hub.extraEnv.OAUTH2_USERDATA_URL"
    value = "https://${local.cognito_domain}/oauth2/userInfo"
  }

  set {
    name = "hub.config.GenericOAuthenticator.client_id"
    value = aws_cognito_user_pool_client.client.id
  }

  set {
    name = "hub.config.GenericOAuthenticator.client_secret"
    value = aws_cognito_user_pool_client.client.client_secret
  }
}

data "kubernetes_service" "proxy_public" {
  depends_on = [helm_release.jupyterhub]
  metadata {
    name = "proxy-public"
    namespace = "daskhub"
  }
}

data "aws_elb" "proxy_public" {
  name = replace(
    data.kubernetes_service.proxy_public.status.0.load_balancer.0.ingress.0.hostname,
    "/-.*/",
    "")
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

  # All static settings belong in the following YAML
  values = [
    "${file("yaml/dask-gateway-values.yaml")}"
  ]

  # Settings which depend on Terraform resources should be set separately
  set {
    name  = "gateway.auth.jupyterhub.apiToken"
    value = random_id.daskhub_token.hex
  }
}
