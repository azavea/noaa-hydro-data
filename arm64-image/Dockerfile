FROM jupyter/scipy-notebook:notebook-6.4.8

RUN conda install -y geopandas=0.10.* xarray=2022.3.* zarr=2.11.* h5netcdf=0.14.* fastparquet=0.8.*

WORKDIR /opt/src/

ENV PYTHONPATH=/opt/src/noaa/:$PYTHONPATH

CMD ["bash"]