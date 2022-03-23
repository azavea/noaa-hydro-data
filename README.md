# NOAA Phase 2 Hydrological Data Processing

## Docker Setup

This describes how to build and run a Docker image for running various notebooks.

```
docker build -t noaa-hydro-data -f Dockerfile .
```

Run the container as follows, making the appropriate substitutions if you are not Lewis. The `--platform linux/amd64` flag is only needed if running on an ARM64 machine like a Macbook Pro M1.

```
docker run --rm -it \
    --ipc=host -u root \
    --platform linux/amd64 \
    -v /Users/lewfish/projects/noaa-hydro-data/:/opt/src/ \
    -v /Users/lewfish/data:/opt/data \
    -v /Users/lewfish/.aws:/home/jovyan/.aws:ro \
    --network noaa-net \
    -e AWS_PROFILE=raster-vision \
    -p 8888:8888 noaa-hydro-data
```

In the container, run the notebook server and then navigate to the URL that is provided on the host machine.

```
jupyter notebook --ip=0.0.0.0 --no-browser --allow-root
```

## Notebooks

Here is a summary of the Jupyter [notebooks](notebooks/) in this repo.

* [nhd_nwm.ipynb](notebooks/nhd_nwm.ipynb): Shows how to get a HUC by id, query NHD for all reaches within the HUC, and then query NWM (in Zarr format) to get gridded and reach-based data. Assumes that a sample of NHDPlus V2 and NHDPlus HR have been loaded locally following the instructions above.
* [save_nwm_sample.ipynb](notebooks/save_nwm_sample.ipynb): Saves a sample of NWM in Zarr and Parquet formats.
* [benchmark_zarr_parquet.ipynb](notebooks/benchmark_zarr_parquet.ipynb): We want to see if it's faster to query reach-based data in NWM when it is stored in Parquet since it has more of a tabular flavor than the gridden datasets. This notebook implements a a rudimentary benchmark of the speed of querying NWM in Zarr vs. Parquet format.
* [save_nhd_extract.ipynb](notebooks/save_nhd_extract.ipynb): Saves a GeoJSON file for each HUC in NHD containing the reach geometries and associated COMID fields. This is so that we can perform other workflows without needing an NHD database running.
* [hydrotools_test.ipynb](notebooks/hydrotools_test.ipynb): Shows how to use the Hydrotools library to compare predicted and observed streamflow levels at sites within a HUC.
* [archive_nwm_zarr.ipynb](notebooks/archive_nwm_zarr.ipynb): Shows how to append grid-based NWM predictions to a Zarr file in order to archive them.
* [archive_nwm_parquet.ipynb](notebooks/archive_nwm_parquet.ipynb): Shows how to append point-based NWM predictions to a Parquet file in order to archive them.

## Local Database Setup

These instructions are for setting up a local copy of NHDPlus V2 and NHDPlus HR which is used in some notebooks. If a notebook requires this step, it should say so within its documentation.

First, create a Docker bridge network so that the main container can communicate with a PostGIS container.

```
docker network create noaa-net
```

Next, run a PostGIS container connected to this network.

```
docker run --name noaa-db -e POSTGRES_PASSWORD=mysecretpassword --network noaa-net -p 5432:5432 -d postgis/postgis
```

Run the `psql` database console using:

```
docker exec -ti noaa-db psql -U postgres
```

Download a [sample](https://edap-ow-data-commons.s3.amazonaws.com/NHDPlusV21/Data/NHDPlusMA/NHDPlusV21_MA_02_NHDSnapshot_04.7z) of NHDPlus V2 which has the `nhdflowline` table with `comid` field that is used to reference reaches in NWM. This field is not available (to our knowledge) in NHDPlus HR. Then, uncompress it and load it into the database.

```
# in psql
CREATE DATABASE nhdplusv2;
\c nhdplusv2;

# on host machine
ogr2ogr -f "PostgreSQL" PG:"host=localhost port=5432 user='postgres' password='mysecretpassword' \
    dbname='nhdplusv2'" <data directory>/NHDPlusMA/NHDPlus02/NHDSnapshot/Hydrography -overwrite -progress --config PG_USE_COPY YES

# in psql
create extension postgis;
```

Then, follow similar steps to load a [sample](https://prd-tnm.s3.amazonaws.com/StagedProducts/Hydrography/NHDPlusHR/Beta/GDB/NHDPLUS_H_0204_HU4_GDB.zip) of the NHDPlus HR dataset which has the `wbdhu12` table containing HUC 12 polygons. This table is not present in NHDPlus V2. 

```
# in psql
CREATE DATABASE nhdplushr;
\c nhdplushr;

# on host machine
ogr2ogr -f "PostgreSQL" PG:"host=localhost port=5432 user='postgres' password='mysecretpassword' \
    dbname='nhdplushr'" <data directory>/NHDPLUS_H_0204_HU4_GDB/NHDPLUS_H_0204_HU4_GDB.gdb -overwrite -progress --config PG_USE_COPY YES

# in psql
create extension postgis;
```

