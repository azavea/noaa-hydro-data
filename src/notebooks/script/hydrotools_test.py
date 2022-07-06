#!/usr/bin/env python
# coding: utf-8

# # Use Hydrotools to measure error in streams gauge forecasts against observations
# 
# Limitations noted:
# * Gauge values sometimes have extreme, seemingly anomalous values that need to be filtered out
# * Can only get forecasts for the past day from the API
# * It is not clear how to find the locations of gauges based on their IDs
# 

get_ipython().run_cell_magic('javascript', '', '// Stop jupyter from scrolling whenever a cell is executed.\nIPython.OutputArea.prototype._should_scroll = function(lines) {\n    return false;\n}\n')


# # Get the observed streamflow for gauges within a HUC for the last day

from hydrotools.nwis_client import IVDataService
import pandas as pd
from hydrotools.nwm_client import http as nwm
import geopandas as gpd


yesterday_ts = (pd.Timestamp.utcnow() - pd.Timedelta("1D"))
yesterday = yesterday_ts.strftime("%Y-%m-%d")
today = pd.Timestamp.utcnow().strftime("%Y-%m-%d")


service = IVDataService()
huc = '02040203'
gauge_df = service.get(huc='02040203', startDT=yesterday, endDT=today)


gauge_df.head()


huc_sites = gauge_df.usgs_site_code.unique()
huc_sites


# Filter out negative gauge value, which are huge numbers and seem anomalous. Need to research this more.
print(gauge_df.value.describe())
good_inds = gauge_df.value >= 0
gauge_df = gauge_df[good_inds]
gauge_df.value.hist()


# # Get NWM forecast for the last day

# This forecast API only support getting the last day.
ref_time = yesterday_ts.strftime("%Y%m%dT%-HZ")
server = "https://nomads.ncep.noaa.gov/pub/data/nccf/com/nwm/prod/"
model_data_service = nwm.NWMDataService(server)
forecast_df = model_data_service.get(
    configuration = "short_range",
    reference_time = ref_time)


forecast_df = forecast_df[forecast_df.usgs_site_code.isin(huc_sites)]
forecast_df = forecast_df.rename({'value_time': 'value_date', 'reference_time': 'reference_date'}, axis='columns')
forecast_df.head()


# # Merge the observations and predictions and calculate the average absolute error grouped by site.

merged_df = forecast_df.merge(
    gauge_df, on=['usgs_site_code', 'value_date'], how='inner', 
    suffixes=['_forecast', '_gauge'])
merged_df.head()


merged_df = merged_df[['usgs_site_code', 'value_date', 'value_forecast', 'value_gauge', 'nwm_feature_id']]


meters2feet = 3.28084


# Convert units to f^3 to be comparable to the observed values.
merged_df['value_forecast_f3'] = merged_df['value_forecast'] * (meters2feet ** 3)


merged_df['err'] = (merged_df['value_forecast_f3'] - merged_df['value_gauge']).abs()


merged_df.head()


grouped_err = merged_df.groupby('usgs_site_code').agg('mean')


grouped_err


# This assumes that the dataset containing the locations of stream gauges is stored locally 
# in the following directory. This dataset can be downloaded from 
# https://www.sciencebase.gov/catalog/item/577445bee4b07657d1a991b6
site_geoms = gpd.read_file('/opt/data/noaa/GageLoc/')
site_geoms = site_geoms[['FLComID', 'geometry']]
site_geoms = site_geoms.rename(columns={'FLComID': 'nwm_feature_id'})
site_geoms.head()


grouped_err['nwm_feature_id'] = grouped_err['nwm_feature_id'].astype(int)


geom_grouped_err = grouped_err.merge(site_geoms, on=['nwm_feature_id'], how='inner')
geom_grouped_err.head()


# # Plot error

geom_grouped_err = gpd.GeoDataFrame(geom_grouped_err)
geom_grouped_err.plot(column='err', legend=True)


import hvplot.pandas # noqa: adds hvplot method to pandas objects


geom_grouped_err.hvplot(global_extent=True, frame_height=450, tiles=True, c='err')
# TODO Zoom in to the area with the points programmatically. I tried a bit, but couldn't figure this out.




