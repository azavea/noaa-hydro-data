FROM jupyter/scipy-notebook:notebook-6.4.8

RUN conda install -y geopandas xarray zarr h5netcdf

WORKDIR /opt/src/

ENV PYTHONPATH=/opt/src/noaa/:$PYTHONPATH

CMD ["bash"]