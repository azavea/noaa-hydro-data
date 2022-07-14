#!/usr/bin/env python
# coding: utf-8

from dask import dataframe as dd
from dask.distributed import Client
from dask_gateway import Gateway

import pandas as pd
import xarray as xr
import fsspec
import s3fs


# Connect to existing cluster using cluster.name

# This constant needs to be set!
cluster_name = ''
gateway = Gateway()
cluster = gateway.connect(cluster_name)
client = cluster.get_client()


comid_uri = 's3://azavea-noaa-hydro-data/noaa/huc2-comids.json'
zarr_uri = 's3://azavea-noaa-hydro-data/esip-experiments/datasets/reanalysis-chrtout/zarr/lf/07-07-2022c/nwm-subset.zarr'
out_root_uri = 's3://azavea-noaa-hydro-data/esip-experiments/datasets/reanalysis-chrtout/parquet/lf/07-13-2022a'
parq_uri = join(out_root_uri, 'nwm-subset')

ds = xr.open_zarr(fsspec.get_mapper(zarr_subsets_uri))
ds


def part_namer(yrmon):
    """
    >>> fns = [part_namer(i) for i in range(1990,1995)]
    >>> [fn(i) for i in range(3) for fn in fns]
    """
    if isinstance(yrmon, str):
        yrmon = int(yrmon)
        
    def fn(idx):
        return f"{yrmon:06}-part.{idx:02}.parquet"
    
    return fn


years = [1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999]
for yr in years:
      df01 = ds.sel(time=f'{yr}-01').to_dask_dataframe(); dd.to_parquet(df01, ds_path, engine='pyarrow', name_function=part_namer(f'{yr}01'), write_metadata_file=True); del df01; print(f'wrote {yr}-01')
      df02 = ds.sel(time=f'{yr}-02').to_dask_dataframe(); dd.to_parquet(df02, ds_path, engine='pyarrow', name_function=part_namer(f'{yr}02'), write_metadata_file=True); del df02; print(f'wrote {yr}-02')
      df03 = ds.sel(time=f'{yr}-03').to_dask_dataframe(); dd.to_parquet(df03, ds_path, engine='pyarrow', name_function=part_namer(f'{yr}03'), write_metadata_file=True); del df03; print(f'wrote {yr}-03')
      df04 = ds.sel(time=f'{yr}-04').to_dask_dataframe(); dd.to_parquet(df04, ds_path, engine='pyarrow', name_function=part_namer(f'{yr}04'), write_metadata_file=True); del df04; print(f'wrote {yr}-04')
      df05 = ds.sel(time=f'{yr}-05').to_dask_dataframe(); dd.to_parquet(df05, ds_path, engine='pyarrow', name_function=part_namer(f'{yr}05'), write_metadata_file=True); del df05; print(f'wrote {yr}-05')
      df06 = ds.sel(time=f'{yr}-06').to_dask_dataframe(); dd.to_parquet(df06, ds_path, engine='pyarrow', name_function=part_namer(f'{yr}06'), write_metadata_file=True); del df06; print(f'wrote {yr}-06')
      df07 = ds.sel(time=f'{yr}-07').to_dask_dataframe(); dd.to_parquet(df07, ds_path, engine='pyarrow', name_function=part_namer(f'{yr}07'), write_metadata_file=True); del df07; print(f'wrote {yr}-07')
      df08 = ds.sel(time=f'{yr}-08').to_dask_dataframe(); dd.to_parquet(df08, ds_path, engine='pyarrow', name_function=part_namer(f'{yr}08'), write_metadata_file=True); del df08; print(f'wrote {yr}-08')
      df09 = ds.sel(time=f'{yr}-09').to_dask_dataframe(); dd.to_parquet(df09, ds_path, engine='pyarrow', name_function=part_namer(f'{yr}09'), write_metadata_file=True); del df09; print(f'wrote {yr}-09')
      df10 = ds.sel(time=f'{yr}-10').to_dask_dataframe(); dd.to_parquet(df10, ds_path, engine='pyarrow', name_function=part_namer(f'{yr}10'), write_metadata_file=True); del df10; print(f'wrote {yr}-10')
      df11 = ds.sel(time=f'{yr}-11').to_dask_dataframe(); dd.to_parquet(df11, ds_path, engine='pyarrow', name_function=part_namer(f'{yr}11'), write_metadata_file=True); del df11; print(f'wrote {yr}-11')
      df12 = ds.sel(time=f'{yr}-12').to_dask_dataframe(); dd.to_parquet(df12, ds_path, engine='pyarrow', name_function=part_namer(f'{yr}12'), write_metadata_file=True); del df12; print(f'wrote {yr}-12')

## ds had 2000-01-01!
df = ds.sel(time='2000-01').to_dask_dataframe()


dd.to_parquet(df, ds_path, engine='pyarrow', name_function=part_namer('200001'), write_metadata_file=True)
del df

