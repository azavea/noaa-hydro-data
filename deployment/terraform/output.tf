output "region" {
  value = var.aws_region
}

output "cluster_name" {
  value = local.cluster_name
}

output "cluster_arn" {
  value = module.eks.cluster_arn
}
