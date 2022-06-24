# resource "aws_security_group" "remote_access" {
#   name_prefix = "${var.app_name}-remote-access"
#   description = "Allow remote SSH access"
#   vpc_id      = module.vpc.vpc_id

#   ingress {
#     description = "SSH access"
#     from_port   = 22
#     to_port     = 22
#     protocol    = "tcp"
#     cidr_blocks = ["10.0.0.0/8"]
#   }

#   egress {
#     from_port        = 0
#     to_port          = 0
#     protocol         = "-1"
#     cidr_blocks      = ["0.0.0.0/0"]
#     ipv6_cidr_blocks = ["::/0"]
#   }

#   tags = local.tags
# }

# resource "aws_security_group" "additional" {
#   name_prefix = "${var.app_name}-additional"
#   vpc_id      = module.vpc.vpc_id

#   ingress {
#     from_port = 22
#     to_port   = 22
#     protocol  = "tcp"
#     cidr_blocks = [
#       "10.0.0.0/8",
#       "172.16.0.0/12",
#       "192.168.0.0/16",
#     ]
#   }

#   tags = local.tags
# }
