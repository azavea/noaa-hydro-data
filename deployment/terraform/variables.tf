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

variable "aws_ecr_account_id" {
  description = "Make sure this matches your aws_region; see https://docs.aws.amazon.com/eks/latest/userguide/add-ons-images.html"
  default = "602401143452"
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

variable "base_instance_type" {
  type = string
  description = "The instance type to use for the always-on core instance running system pods"
  default = "t3.medium"
}

variable "base_instance_capacity_type" {
  type = string
  description = "The capacity type of the always-on core instance (SPOT, ON_DEMAND)"
  default = "ON_DEMAND"
}

variable "instance_types" {
  type = list
  default = ["m4.xlarge", "m6i.large", "m5.large", "m5n.large", "m5zn.large"]
}

variable "auth_domain_prefix" {
  type = string
  description = "Domain prefix for Cognito OAuth"
}

variable "r53_public_hosted_zone" {
  type = string
  description = "Hosted zone name for this application"
}

variable "r53_zone_id" {
  type = string
  description = "Zone ID of existing hosted zone"
}

variable "user_map" {
  type = list(object({username: string, userarn: string, groups: list(string)}))
  description = "A list of {\"username\": string, \"userarn\": string, \"groups\": list(string)} objects describing the users who should have RBAC access to the cluster; note: system:masters should be used for admin access"
  default = []
}

variable "letsencrypt_contact_email" {
  type = string
  description = "Contact email for Let's Encrypt (jupyterhub HTTPS certificate provider)"
}

variable "google_identity_client_id" {
  type = string
  description = "Client ID for Google identity provider"
}

variable "google_identity_client_secret" {
  type = string
  description = "Client ID for Google identity provider"
}

variable "pangeo_notebook_version" {
  type = string
  description = "Version of pangeo"
  default = "2022.05.18"
}

variable "jupyter_notebook_s3_bucket" {
  type = string
  description = "The name of the bucket in which to store user notebooks"
}
