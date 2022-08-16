resource "random_id" "daskhub_token" {
  byte_length = 32
}

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
  timeout    = 600

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
    name = "singleuser.image.name"
    value = aws_ecr_repository.pangeo_s3contents.repository_url
  }

  set {
    name = "singleuser.image.tag"
    value = var.pangeo_notebook_version
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

resource "aws_iam_role" "daskhub" {
  name = "daskhub-irsa"
  description = "IRSA trust policy for Daskhub pods in default service account"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "${module.eks.oidc_provider_arn}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${module.eks.oidc_provider}:aud": "sts.amazonaws.com",
          "${module.eks.oidc_provider}:sub": "system:serviceaccount:daskhub:default"
        }
      }
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "irsa_s3_full_access" {
  role = aws_iam_role.daskhub.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"

  depends_on = [helm_release.jupyterhub]
}

module "daskhub_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"

  create_role = true
  role_name = "daskhub"

  role_policy_arns = {
    s3_full_access = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
  }

  oidc_providers = {
    main = {
      provider = module.eks.oidc_provider
      provider_arn = module.eks.oidc_provider_arn
      namespace_service_accounts = ["daskhub:default"]
    }
  }
}

resource "kubernetes_annotations" "daskhub_iam_annotation" {
  api_version = "v1"
  kind = "ServiceAccount"
  metadata {
    name = "default"
    namespace = "daskhub"
  }
  annotations = {
    "eks.amazonaws.com/role-arn": aws_iam_role.daskhub.arn
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

  # All static settings belong in the following YAML
  values = [
    "${file("yaml/dask-gateway-values.yaml")}"
  ]

  # Settings which depend on Terraform resources should be set separately
  set {
    name  = "gateway.auth.jupyterhub.apiToken"
    value = random_id.daskhub_token.hex
  }

  set {
    name = "gateway.backend.image.name"
    value = aws_ecr_repository.pangeo_s3contents.repository_url
  }

  set {
    name = "gateway.backend.image.tag"
    value = var.pangeo_notebook_version
  }
}
