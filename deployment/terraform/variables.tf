variable "first_cluster_deployment" {
  # We are using IRSA created for permissions.  However, we have to deploy with
  # the policy attached FIRST when creating a fresh cluster, and then turn this
  # off after the cluster/node group is created. Without this initial policy,
  # the VPC CNI fails to assign IPs and nodes cannot join the cluster
  # See https://github.com/aws/containers-roadmap/issues/1666 for more context
  type = bool
  default = true
}

variable "aws_region" {
  default = "us-east-1"
}

variable "app_name" {
  default = "k8s-application"
}

variable "repo_name" {
  type = string
  description = "Name of the Github repo hosting the deployment (for tagging)"
  default = "k8s-deployments"
}

variable "environment" {
  type = string
  description = "Name of target environment (e.g., production, staging, QA, etc.)"
}

variable "cluster_version" {
  type = string
  default = "1.22"
}

variable "instance_types" {
  type = list
  default = ["m4.xlarge", "m6i.large", "m5.large", "m5n.large", "m5zn.large"]
}
