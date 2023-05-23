# NOAA Phase 2 Hydrological Data Processing

## Docker Setup

Run `./scripts/setup` to create the local development container.

Run the notebook server with `./scripts/server` and then navigate to the URL that is provided on the host machine.

## Notebooks

Here is a summary of the Jupyter [notebooks](src/notebooks/) in this repo.

* [nhd_nwm.ipynb](src/notebooks/nhd_nwm.ipynb): Shows how to get a HUC by id, query NHD for all reaches within the HUC, and then query NWM (in Zarr format) to get gridded and reach-based data. Assumes that a sample of NHDPlus V2 and NHDPlus HR have been loaded locally following the instructions above.
* [save_nwm_sample.ipynb](src/notebooks/save_nwm_sample.ipynb): Saves a sample of NWM in Zarr and Parquet formats.
* [benchmark_zarr_parquet.ipynb](src/notebooks/benchmark_zarr_parquet.ipynb): We want to see if it's faster to query reach-based data in NWM when it is stored in Parquet since it has more of a tabular flavor than the gridden datasets. This notebook implements a a rudimentary benchmark of the speed of querying NWM in Zarr vs. Parquet format.
* [save_nhd_extract.ipynb](src/notebooks/save_nhd_extract.ipynb): Saves a GeoJSON file for each HUC in NHD containing the reach geometries and associated COMID fields. This is so that we can perform other workflows without needing an NHD database running.
* [hydrotools_test.ipynb](src/notebooks/hydrotools_test.ipynb): Shows how to use the Hydrotools library to compare predicted and observed streamflow levels at sites within a HUC.
* [archive_nwm_zarr.ipynb](src/notebooks/archive_nwm_zarr.ipynb): Shows how to append grid-based NWM predictions to a Zarr file in order to archive them.
* [archive_nwm_parquet.ipynb](src/notebooks/archive_nwm_parquet.ipynb): Shows how to append point-based NWM predictions to a Parquet file in order to archive them.
* [rechunker_test.ipynb](src/notebooks/rechunker_test.ipynb): Test rechunker library on NWM 
* [save_huc2_comids.ipynb](src/notebooks/save_huc2_comids.ipynb): Save COMIDs for HUC2 02 which is used for testing purposes.
* [huc8_streamflow_query.ipynb](src/notebooks/huc8_streamflow_query.ipynb): Run benchmarks using HUC8 streamflow query
* [rechunk_zarr_subset.ipynb](src/notebooks/rechunk_zarr_subset.ipynb): Save a subset of NWM and rechunk it to use in benchmarking experiments.
* [convert_netcdf_to_zarr.ipynb](src/notebooks/convert_netcdf_to_zarr.ipynb): Convert a sample NWM Predictions dataset to Zarr. First do it by downloading the source files and converting locally, and then do it by reading from and writing to S3 directly.
* [compare_rechunked_zarr.ipynb](src/notebooks/compare_rechunked_zarr.ipynb): Compare benchmarks run on the base Zarr with the Rechunked version.

## Local Database Setup

These instructions are for setting up a local copy of NHDPlus V2 and NHDPlus HR which is used in some notebooks. If a notebook requires this step, it should say so within its documentation.

While the server is running with `./scripts/server`, run the `psql` database console using:

```
./scripts/psql
```

Download a [sample](https://edap-ow-data-commons.s3.amazonaws.com/NHDPlusV21/Data/NHDPlusMA/NHDPlusV21_MA_02_NHDSnapshot_04.7z) of NHDPlus V2 which has the `nhdflowline` table with `comid` field that is used to reference reaches in NWM. This field is not available (to our knowledge) in NHDPlus HR. Then, uncompress it and load it into the database.

```
# in psql
CREATE DATABASE nhdplusv2;
\c nhdplusv2;
CREATE EXTENSION postgis;

# on host machine
ogr2ogr -f "PostgreSQL" PG:"host=localhost port=5432 user='postgres' password='password' \
    dbname='nhdplusv2'" data/NHDPlusMA/NHDPlus02/NHDSnapshot/Hydrography -overwrite -progress --config PG_USE_COPY YES -lco GEOMETRY_NAME=wkb_geometry
```

Then, follow similar steps to load a [sample](https://prd-tnm.s3.amazonaws.com/StagedProducts/Hydrography/NHDPlusHR/Beta/GDB/NHDPLUS_H_0204_HU4_GDB.zip) of the NHDPlus HR dataset which has the `wbdhu12` table containing HUC 12 polygons. This table is not present in NHDPlus V2. 

```
# in psql
CREATE DATABASE nhdplushr;
\c nhdplushr;
CREATE EXTENSION postgis;

# on host machine
ogr2ogr -f "PostgreSQL" PG:"host=localhost port=5432 user='postgres' password='password' \
    dbname='nhdplushr'" data/NHDPLUS_H_0204_HU4_GDB/NHDPLUS_H_0204_HU4_GDB.gdb -overwrite -progress --config PG_USE_COPY YES -lco GEOMETRY_NAME=wkb_geometry
```

## Other Setup Docs
 
* [Setting up DaskHub on Kubernetes](docs/daskhub-setup.md)

## Running on AWS Batch

* Make a new ECR repository.
* Make a new Batch job definition modeled after `lfishgoldNoaaHydroData`. This should point to the above ECR repo and use the `queueCPU` job queue.
* Set the `NOAA_ECR_IMAGE_NAME` environment variable to the ECR repo created above.
* Build the Docker image using `./scripts/update` and then upload the image to ECR using `./scripts/ecr_publish`.
* Run commands in the container on Batch using something like the following assuming you have AWS CLI v2: 
```
aws batch submit-job --job-name <a job name> --job-queue queueCPU --job-definition <the batch job definition> \
    --container-overrides '{"command": ["echo", "hello", "world"], "resourceRequirements": [{"value": "<the number of cores to use>", "type": "VCPU"}]}' 
```
