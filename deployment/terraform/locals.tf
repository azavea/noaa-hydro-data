locals {
  region = var.aws_region
  cluster_name = "${var.app_name}-eks-${random_string.suffix.result}"
  storage_class_name = "${var.app_name}-ebs"

  cognito_domain = "${var.auth_domain_prefix}.auth.${var.aws_region}.amazoncognito.com"

  tags = {
    Name    = var.app_name
    GithubRepo = var.repo_name
    GithubOrg  = "azavea"
  }
}
