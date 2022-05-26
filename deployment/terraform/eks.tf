module "eks" {
  source          = "terraform-aws-modules/eks/aws"

  cluster_name                    = local.cluster_name
  cluster_version                 = var.cluster_version
  cluster_endpoint_private_access = true
  cluster_endpoint_public_access  = true

  # Might be able to skip the IPv6 difficulties (do we need ipv6?)
  # # IPV6
  # cluster_ip_family = "ipv6"
  #
  # # TODO - remove this policy once AWS releases a managed version similar to
  # # AmazonEKS_CNI_Policy (IPv4)
  # create_cni_ipv6_iam_policy = var.first_cluster_deployment

  cluster_addons = {
    coredns = {
      resolve_conflicts = "OVERWRITE"
    }
    kube-proxy = {}
    vpc-cni = {
      resolve_conflicts        = "OVERWRITE"
      service_account_role_arn = module.vpc_cni_irsa.iam_role_arn
    }
  }

  # cluster_encryption_config = [{
  #   provider_key_arn = aws_kms_key.eks.arn
  #   resources        = ["secrets"]
  # }]

  cluster_tags = {
    # This should not affect the name of the cluster primary security group
    # Ref: https://github.com/terraform-aws-modules/terraform-aws-eks/pull/2006
    # Ref: https://github.com/terraform-aws-modules/terraform-aws-eks/pull/2008
    Name = var.app_name
  }

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  manage_aws_auth_configmap = true

  # Extend cluster security group rules
  cluster_security_group_additional_rules = {
    egress_nodes_ephemeral_ports_tcp = {
      description                = "To node 1025-65535"
      protocol                   = "tcp"
      from_port                  = 1025
      to_port                    = 65535
      type                       = "egress"
      source_node_security_group = true
    }
  }

  # Extend node-to-node security group rules
  node_security_group_additional_rules = {
    ingress_self_all = {
      description = "Node to node all ports/protocols"
      protocol    = "-1"
      from_port   = 0
      to_port     = 0
      type        = "ingress"
      self        = true
    }
    egress_all = {
      description      = "Node all egress"
      protocol         = "-1"
      from_port        = 0
      to_port          = 0
      type             = "egress"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    }
  }

  eks_managed_node_group_defaults = {
    ami_type       = "AL2_x86_64"
    instance_types = var.instance_types

    iam_role_attach_cni_policy = var.first_cluster_deployment
  }

  eks_managed_node_groups = {
    base = {
      create_launch_template = false
      launch_template_name = ""
      instance_types = ["t3.small"]
      capacity_type = "SPOT"
      min_size = 1
      max_size = 1
      desired_size = 1
    }

    # Default node group - as provided by AWS EKS
    on_demand = {
      # By default, the module creates a launch template to ensure tags are
      # propagated to instances, etc., so we need to disable it to use the
      # default template provided by the AWS EKS managed node group service
      create_launch_template = false
      launch_template_name   = ""

      disk_size = 50

      min_size = 0
      max_size = 3
      desired_size = 0

      # Remote access cannot be specified with a launch template
      remote_access = {
        ec2_ssh_key               = aws_key_pair.this.key_name
        source_security_group_ids = [aws_security_group.remote_access.id]
      }

      instance_types = var.instance_types
    }

    spot = {
      create_launch_template = false
      launch_template_name   = ""

      min_size = 0
      max_size = 3
      desired_size = 0

      instance_types = var.instance_types
      capacity_type = "SPOT"
    }

    # Default node group - as provided by AWS EKS using Bottlerocket
    bottlerocket = {
      # By default, the module creates a launch template to ensure tags are
      # propagated to instances, etc., so we need to disable it to use the
      # default template provided by the AWS EKS managed node group service
      create_launch_template = false
      launch_template_name   = ""

      min_size = 0
      max_size = 3
      desired_size = 0

      ami_type = "BOTTLEROCKET_x86_64"
      platform = "bottlerocket"

      instance_types = var.instance_types
      capacity_type = "SPOT"
    }

  }

  tags = local.tags
}

resource "null_resource" "kubectl" {
  depends_on = [module.eks.kubeconfig]
  provisioner "local-exec" {
    command = "aws eks --region ${var.aws_region} update-kubeconfig --name ${module.eks.cluster_id}"
  }
}
