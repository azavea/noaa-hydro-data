# NOAA Phase 2 Hydrological Data Processing

## NHD/NWM Data Exploration Notebook

These instructions are for setting up a local copy of NHDPlus V2 and NHDPlus HR, and then running a notebook that shows how to query NWM (stored in Zarr on S3) by HUC.

### Database setup

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

### Run notebook

Build a Docker image for running the notebook.

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

The notebook is in [notebooks/nhd_nwm.ipynb](notebooks/nhd_nwm.ipynb). Enjoy!

### Notebooks for benchmarking querying NWM in Zarr vs. Parquet format

We want to see if it's faster to query reach-based data in NWM when it is stored in Parquet since it has more of a tabular flavor than the gridden datasets. There is a [notebook](notebooks/save_nwm_sample.ipynb) for saving a sample of NWM in Zarr and Parquet formats, and another [notebook](notebooks/benchmark_zarr_parquet.ipynb) for benchmarking queries against it.

### Notebook for saving extract of NHD

There is a [notebook](notebooks/save_nhd_extract.ipynb) to save a GeoJSON file for each HUC in NHD containing the reach geometries and associated COMID fields. This is so that we can perform other workflows without needing an NHD database running.

### Notebook for testing HydroTools

There is a [notebook](notebooks/hydrotools_test.ipynb) that shows how to use the Hydrotools library to compare predicted and observed streamflow levels at sites within a HUC.