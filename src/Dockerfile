FROM pangeo/pangeo-notebook:latest
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
         psycopg2 \
         holoviews \
         geopandas" \
    && apt-get update && apt-get install -y $buildDeps $deps --no-install-recommends \
    && conda install --name notebook --yes $condaDeps \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove $buildDeps

ENV PYTHONPATH=/opt/src/noaa/:$PYTHONPATH

ENTRYPOINT ["jupyter"]

CMD ["notebook", "--ip=0.0.0.0", "--no-browser", "--allow-root"]
