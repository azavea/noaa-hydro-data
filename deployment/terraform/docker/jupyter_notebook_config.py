from s3contents import S3ContentsManager
import os

fulluser = os.environ['JUPYTERHUB_USER']
ix = fulluser.find('@')
if ix != -1:
    fulluser = fulluser[:ix]

c = get_config()

# Tell Jupyter to use S3ContentsManager
c.ServerApp.contents_manager_class = S3ContentsManager
c.S3ContentsManager.bucket = "noaa-notebooks"
c.S3ContentsManager.prefix = fulluser

# Fix JupyterLab dialog issues
#c.ServerApp.root_dir = ""
