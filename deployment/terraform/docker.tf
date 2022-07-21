data "aws_caller_identity" "this" {}
data "aws_ecr_authorization_token" "token" {}

provider "docker" {
  host = "unix:///var/run/docker.sock"

  registry_auth {
    address  = format("%v.dkr.ecr.%v.amazonaws.com", data.aws_caller_identity.this.account_id, var.aws_region)
    username = data.aws_ecr_authorization_token.token.user_name
    password = data.aws_ecr_authorization_token.token.password
    config_file = pathexpand("~/.docker/config.json")
  }
}

resource "aws_ecr_repository" "pangeo_s3contents" {
  name                 = "pangeo-s3contents"
  image_tag_mutability = "MUTABLE"
}

resource "docker_registry_image" "pangeo_s3contents" {
  name = format(
    "%v:%v",
    aws_ecr_repository.pangeo_s3contents.repository_url,
    var.pangeo_notebook_version
  )

  depends_on = [
    local_file.jupyter_notebook_config,
  ]

  build {
    version = "2" # Enable Docker BuildKit
    context = "docker/"
    dockerfile = "Dockerfile.pangeo_s3contents"
    build_args = {
      PANGEO_VERSION : var.pangeo_notebook_version
    }
    auth_config {
      host_name  = aws_ecr_repository.pangeo_s3contents.repository_url
      user_name = data.aws_ecr_authorization_token.token.user_name
      password = data.aws_ecr_authorization_token.token.password
    }
  }
}

resource "local_file" "jupyter_notebook_config" {
  filename = "${path.module}/docker/jupyter_notebook_config.py"
  content = <<EOF
from s3contents import S3ContentsManager
import os

fulluser = os.environ['JUPYTERHUB_USER']
ix = fulluser.find('@')
if ix != -1:
    fulluser = fulluser[:ix]

c = get_config()

# Tell Jupyter to use S3ContentsManager
c.ServerApp.contents_manager_class = S3ContentsManager
c.S3ContentsManager.bucket = "${var.jupyter_notebook_s3_bucket}"
c.S3ContentsManager.prefix = fulluser

# Fix JupyterLab dialog issues
#c.ServerApp.root_dir = ""
EOF
}
