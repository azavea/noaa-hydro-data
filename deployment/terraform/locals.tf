locals {
  region = var.aws_region
  cluster_name = "${var.app_name}-eks-${random_string.suffix.result}"

  tags = {
    Name    = var.app_name
    GithubRepo = var.repo_name
    GithubOrg  = "azavea"
  }
}
