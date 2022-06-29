resource "aws_cognito_user_pool" "pool" {
  name = "${var.app_name}-pool"

  username_attributes = ["email"]
}

resource "aws_cognito_user_pool_domain" "domain" {
  user_pool_id = aws_cognito_user_pool.pool.id
  domain = var.auth_domain_prefix
}

resource "aws_cognito_resource_server" "resource" {
  identifier = "https://jupyter.${var.r53_public_hosted_zone}"
  name = "jupyter"

  user_pool_id = aws_cognito_user_pool.pool.id

  scope {
    scope_name = "read_product"
    scope_description = "Read product details"
  }

  scope {
    scope_name = "create_product"
    scope_description = "Create a new product"
  }

  scope {
    scope_name = "delete_product"
    scope_description = "Delete a product"
  }
}

resource "aws_cognito_user_pool_client" "client" {
  name = "${var.app_name}-client"
  depends_on = [aws_cognito_identity_provider.provider]

  generate_secret = true
  user_pool_id = aws_cognito_user_pool.pool.id

  callback_urls = ["https://jupyter.${var.r53_public_hosted_zone}/hub/oauth_callback"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows = ["code", "implicit"]
  allowed_oauth_scopes = ["email", "openid"]
  supported_identity_providers = ["COGNITO", "Google"]
}

resource "aws_cognito_identity_provider" "provider" {
  user_pool_id = aws_cognito_user_pool.pool.id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    authorize_scopes = "email"
    client_id = var.google_identity_client_id
    client_secret = var.google_identity_client_secret
  }

  attribute_mapping = {
    email    = "email"
    username = "sub"
  }
}
