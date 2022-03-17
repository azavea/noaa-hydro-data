FROM pangeo/pangeo-notebook:latest

RUN conda install -y psycopg2 holoviews geopandas
RUN pip install hydrotools

WORKDIR /opt/src/

ENV PYTHONPATH=/opt/src/noaa/:$PYTHONPATH

CMD ["bash"]