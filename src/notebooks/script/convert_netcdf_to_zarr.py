#!/usr/bin/env python
# coding: utf-8

import os
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt


# ## Download NetCDF Data
# 
# The NWM Predictions dataset is published as NetCDF files, and available here: https://nomads.ncep.noaa.gov/pub/data/nccf/com/nwm/v2.2/.
# 
# This folder usually has a couple days of data. At the time of this writing, `nwm.20221017` was available.
# 
# Within that folder, we see a number of options:
# 
# ```
# analysis_assim/
# analysis_assim_extend/
# analysis_assim_extend_no_da/
# analysis_assim_hawaii/
# analysis_assim_hawaii_no_da/
# analysis_assim_long/
# analysis_assim_long_no_da/
# analysis_assim_no_da/
# analysis_assim_puertorico/
# analysis_assim_puertorico_no_da/
# forcing_analysis_assim/
# forcing_analysis_assim_extend/
# forcing_analysis_assim_hawaii/
# forcing_analysis_assim_puertorico/
# forcing_medium_range/
# forcing_short_range/
# forcing_short_range_hawaii/
# forcing_short_range_puertorico/
# long_range_mem1/
# long_range_mem2/
# long_range_mem3/
# long_range_mem4/
# medium_range_mem1/
# medium_range_mem2/
# medium_range_mem3/
# medium_range_mem4/
# medium_range_mem5/
# medium_range_mem6/
# medium_range_mem7/
# medium_range_no_da/
# short_range/
# short_range_hawaii/
# short_range_hawaii_no_da/
# short_range_puertorico/
# short_range_puertorico_no_da/
# usgs_timeslices/
# ```
# 
# We begin with the short-range forecast, which has Streamflow Channel Routing files for 18 cycles at midnight:
# 
# ```
# nwm.t00z.short_range.channel_rt.f001.conus.nc
# nwm.t00z.short_range.channel_rt.f002.conus.nc
# nwm.t00z.short_range.channel_rt.f003.conus.nc
# nwm.t00z.short_range.channel_rt.f004.conus.nc
# nwm.t00z.short_range.channel_rt.f005.conus.nc
# nwm.t00z.short_range.channel_rt.f006.conus.nc
# nwm.t00z.short_range.channel_rt.f007.conus.nc
# nwm.t00z.short_range.channel_rt.f008.conus.nc
# nwm.t00z.short_range.channel_rt.f009.conus.nc
# nwm.t00z.short_range.channel_rt.f010.conus.nc
# nwm.t00z.short_range.channel_rt.f011.conus.nc
# nwm.t00z.short_range.channel_rt.f012.conus.nc
# nwm.t00z.short_range.channel_rt.f013.conus.nc
# nwm.t00z.short_range.channel_rt.f014.conus.nc
# nwm.t00z.short_range.channel_rt.f015.conus.nc
# nwm.t00z.short_range.channel_rt.f016.conus.nc
# nwm.t00z.short_range.channel_rt.f017.conus.nc
# nwm.t00z.short_range.channel_rt.f018.conus.nc
# ```
# 
# Let's download these files:

PREDICTIONS_DATADIR = '/opt/data/nwm-predictions'


get_ipython().system("mkdir -p /opt/data/nwm-predictions && cd /opt/data/nwm-predictions && seq -f 'https://nomads.ncep.noaa.gov/pub/data/nccf/com/nwm/v2.2/nwm.20221017/short_range/nwm.t00z.short_range.channel_rt.f%03g.conus.nc' 1 18 | xargs -P 0 -n 1 wget -q")

os.listdir(PREDICTIONS_DATADIR)


# ## Sample Downloaded Data
# 
# Before we do any further work with it, let's open one of the files in the dataset and take a look at it.

ds = xr.open_dataset(f'{PREDICTIONS_DATADIR}/nwm.t00z.short_range.channel_rt.f001.conus.nc')
ds


ds['streamflow'].plot()


# ## Convert to Zarr
# 
# Let's open the entire dataset, using [recommendations from XArray on reading multiple NetCDF files](https://docs.xarray.dev/en/stable/user-guide/io.html#reading-multi-file-datasets).
# 

get_ipython().run_cell_magic('time', '', "ds = xr.open_mfdataset(f'{PREDICTIONS_DATADIR}/*.nc',\n                       parallel=True,\n                       engine='h5netcdf',\n                       concat_dim='time',\n                       combine='nested',\n                       data_vars=['streamflow'],\n                       coords='minimal',\n                       compat='override'\n                      )\nds")


# Now let's convert it to Zarr.

get_ipython().run_cell_magic('time', '', "ds.to_zarr(f'{PREDICTIONS_DATADIR}-channel_rt.zarr', mode='w')")


# ### Compare Dataset Sizes

get_ipython().system('du -sh /opt/data/*')


# ### Check Data Correctness

dsz = xr.open_dataset(f'{PREDICTIONS_DATADIR}-channel_rt.zarr')

all(np.allclose(ds[v].to_numpy(), dsz[v].to_numpy(), equal_nan=True)
    for v in ds.data_vars.keys() if len(ds[v].shape) > 0)

