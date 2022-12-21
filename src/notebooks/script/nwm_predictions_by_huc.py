from pynhd.pynhd import NHD, NHDPlusHR, WaterData
from shapely.geometry import Polygon, MultiLineString
import s3fs
import xarray as xr

from datetime import datetime

huc10 = WaterData('wbd02_20201006').byid('huc2', '02')
huc10.geometry.plot()

flowlines = NHD('flowline_mr').bygeom(huc10.geometry[0].geoms[0])
flowlines.plot()

fs = s3fs.S3FileSystem(anon=True)
today = datetime.now().strftime('%Y%m%d')

netcdf_url = f's3://noaa-nwm-pds/nwm.{today}/short_range/nwm.t00z.short_range.channel_rt.f001.conus.nc'

ds = xr.open_dataset(fs.open(netcdf_url), engine='h5netcdf')

nhd_reaches = set([int(f) for f in flowlines['COMID']])
nwm_reaches = set(ds.feature_id.values)

common_reaches = list(set(nwm_reaches).intersection(set(nhd_reaches)))

sub_ds = ds.sel(feature_id=common_reaches, time=f'{today}T01:00:00')

joined = flowlines.merge(sub_ds['streamflow'].to_dataframe(), left_on='COMID', right_on='feature_id')

ax = huc10.plot(facecolor="none", edgecolor="k", figsize=(9, 9))
joined.plot(ax=ax, column="streamflow", cmap="YlGnBu", legend=True, legend_kwds={"label": "Streamflow (m3/s)"})
ax.figure.set_dpi(100)
