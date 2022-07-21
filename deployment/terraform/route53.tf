#
# Public DNS resources
#
# resource "aws_route53_zone" "external" {
#   name = var.r53_public_hosted_zone

#   tags = {
#     Project = var.app_name
#   }
# }

data "aws_route53_zone" "external" {
  zone_id = var.r53_zone_id
}

resource "aws_route53_record" "jupyterhub" {
  zone_id = data.aws_route53_zone.external.zone_id
  name    = "jupyter.${var.r53_public_hosted_zone}"
  type    = "A"

  alias {
    name                   = data.aws_elb.proxy_public.dns_name
    zone_id                = data.aws_elb.proxy_public.zone_id
    evaluate_target_health = true
  }
}

# resource "aws_alb_listener" "proxy_forward" {
#   load_balancer_arn = data.aws_elb.proxy_public.arn

#   port = "80"
#   protocol = "HTTP"

#   default_action {
#     type = "authenticate-cognito"

#     authenticate_cognito {
#       user_pool_arn       = aws_cognito_user_pool.pool.arn
#       user_pool_client_id = aws_cognito_user_pool_client.client.id
#       user_pool_domain    = aws_cognito_user_pool_domain.domain.domain
#     }
#   }
# }
