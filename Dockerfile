FROM pangeo/pangeo-notebook:latest

RUN conda install -y psycopg2

WORKDIR /opt/src/

ENV PYTHONPATH=/opt/src/noaa/:$PYTHONPATH

COPY ./noaa /opt/src/noaa

CMD ["bash"]