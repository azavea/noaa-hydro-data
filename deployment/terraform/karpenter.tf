resource "helm_release" "karpenter" {
  depends_on       = [module.eks.kubeconfig]
  namespace        = "karpenter"
  create_namespace = true

  name       = "karpenter"
  repository = "https://charts.karpenter.sh"
  chart      = "karpenter"
  version    = "v0.5.3"

  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = module.iam_assumable_role_karpenter.iam_role_arn
  }

  set {
    name  = "controller.clusterName"
    value = local.cluster_name
  }

  set {
    name  = "controller.clusterEndpoint"
    value = module.eks.cluster_endpoint
  }
}

module "karpenter_controller_irsa_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"

  role_name                          = "karpenter-controller"
  attach_karpenter_controller_policy = true

  karpenter_controller_cluster_id         = module.eks.cluster_id
  karpenter_controller_node_iam_role_arns = [for ng in module.eks.eks_managed_node_groups: ng.iam_role_arn]

  oidc_providers = {
    ex = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["karpenter:karpenter"]
    }
  }

  tags = local.tags
}

# Here, we set the behavior of Karpenter; see https://karpenter.sh/v0.6.3/aws/provisioning/
resource "kubectl_manifest" "karpenter_provisioner" {
  yaml_body = <<-YAML
  apiVersion: karpenter.sh/v1alpha5
  kind: Provisioner
  metadata:
    name: default
  spec:
    requirements:
      - key: karpenter.sh/capacity-type
        operator: In
        values: ["spot"]
      - key: node.kubernetes.io/instance-type
        operator: In
        values: ${jsonencode(var.instance_types)}
    limits:
      resources:
        cpu: 1000
    provider:
      subnetSelector:
        kubernetes.io/cluster/${local.cluster_name}: '*'
      securityGroupSelector:
        "aws:eks:cluster-name": ${local.cluster_name}
      tags:
        azavea.com/${var.app_name}: 'provisioner'
      instanceProfile:
        KarpenterNodeInstanceProfile-${local.cluster_name}
    ttlSecondsAfterEmpty: 30
  YAML

  depends_on = [
    helm_release.karpenter,
    null_resource.kubectl
  ]
}
