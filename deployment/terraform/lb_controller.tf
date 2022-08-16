# resource "aws_iam_policy" "lb_controller_policy" {
#   name = "load-balancer-controller-policy"
#   policy = file("json/lb_controller_policy.json")
# }

# resource "aws_iam_role" "load_balancer" {
#   name = "load-balancer-role-trust-policy"

#   assume_role_policy = jsonencode({
#     "Version": "2012-10-17",
#     "Statement": [
#       {
#         "Effect": "Allow",
#         "Principal": {
#           "Federated": module.eks.oidc_provider_arn
#         },
#         "Action": "sts:AssumeRoleWithWebIdentity",
#         "Condition": {
#           "StringEquals": {
#             "${module.eks.oidc_provider}:aud": "sts.amazonaws.com",
#             "${module.eks.oidc_provider}:sub": "system:serviceaccount:kube-system:aws-load-balancer-controller"
#           }
#         }
#       }
#     ]
#   })
# }

# resource "aws_iam_role_policy_attachment" "load-balancer-controller" {
#   role = aws_iam_role.load_balancer.name
#   policy_arn = aws_iam_policy.lb_controller_policy.arn
# }

# resource "kubectl_manifest" "lb_service_account" {
#   yaml_body = <<-YAML
# apiVersion: v1
# kind: ServiceAccount
# metadata:
#   labels:
#     app.kubernetes.io/component: controller
#     app.kubernetes.io/name: aws-load-balancer-controller
#   name: aws-load-balancer-controller
#   namespace: kube-system
#   annotations:
#     eks.amazonaws.com/role-arn: ${aws_iam_role.load_balancer.arn}
#   YAML

#   depends_on = [null_resource.kubectl]
# }

# resource "helm_release" "aws_load_balancer_controller" {
#   depends_on       = [module.eks.kubeconfig]
#   namespace        = "kube-system"
#   create_namespace = false

#   name       = "aws-load-balancer-controller"
#   repository = "https://aws.github.io/eks-charts"
#   chart      = "aws-load-balancer-controller"

#   set {
#     name  = "clusterName"
#     value = local.cluster_name
#   }

#   set {
#     name  = "serviceAccount.create"
#     value = false
#   }

#   set {
#     name  = "serviceAccount.name"
#     value = "aws-load-balancer-controller"
#   }
# }

# module "load_balancer_controller_irsa_role" {
#   source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"

#   role_name                              = "load-balancer-controller"
#   attach_load_balancer_controller_policy = true

#   oidc_providers = {
#     ex = {
#       provider_arn               = module.eks.oidc_provider_arn
#       namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
#     }
#   }

#   tags = local.tags
# }
