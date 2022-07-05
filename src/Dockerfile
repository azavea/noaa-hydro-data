FROM jupyter/scipy-notebook:notebook-6.4.8
USER root

WORKDIR /opt/src
COPY requirements.txt /opt/src/

RUN set -ex \
    && buildDeps=" \
         build-essential \
         libpq-dev" \
    && deps=" \
         postgresql-client" \
    && condaDeps=" \
         psycopg2=2.9.* \
         holoviews=1.14.* \
         geopandas=0.10.* \
         xarray=2022.3.* \
         zarr=2.11.*" \
    && apt-get update && apt-get install -y $buildDeps $deps --no-install-recommends \
    && conda install --yes $condaDeps \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove $buildDeps

ENV PYTHONPATH=/opt/src/noaa/:$PYTHONPATH

CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--no-browser", "--allow-root"]