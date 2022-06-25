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
