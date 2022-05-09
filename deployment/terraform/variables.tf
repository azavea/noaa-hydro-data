variable "aws_region" {
  default = "us-east-1"
}

variable "app_name" {
  default = "k8s-application"
}

variable "environment" {
  type = string
  description = "Name of target environment (e.g., production, staging, QA, etc.)"
}
