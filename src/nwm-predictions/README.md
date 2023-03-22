# Evaluating NWM Streamflow Predictions

The National Water Model (NWM) Predictions Dataset contains [short range, medium range, and long range predictions][1] of various stream metrics for features across the United States. The streamflow predictions are presented as channel point files, in the NetCDF format.

The notebooks in this folder answer two questions:

  1. How does the streamflow prediction vary over time?
  2. How does such analysis done on the NetCDF files compare with the same analysis done in more cloud-friendly formats, such as Zarr or Kerchunk?

## Analyzing Change in Streamflow Predictions Over Time

This is done in the first notebook: [1_evaluating_nwm_streamflow_predictions_netcdf][2]. This picks a HUC to analyze, and fetches all the NHD streams therein. Then it fetches the NWM Predictions for a certain date, from the NetCDF files in the `noaa-nwm-pds` S3 bucket, and intersects the NWM features with the NHD comids. Once we have this subset, we analyze it.

First we pick a single stream to analyze. For that stream, we look at each of the short range predictions, and chart how those predictions change over 24 hours. We graph the standard deviation per hour, and also calculate the average deviation for that stream.

Next, we take that calculation and apply it to all the streams in the HUC. We visualize this variation, observing that the main stem of a river has higher variation than the contributing streams. This makes intuitive sense, since the main stem is absorbing the variation from a large number of contributing streams, and as such has more uncertainty.

## Doing the Analysis using Zarr

The Zarr format is better for cloud querying than NetCDF. However, it requires that the input be first converted to Zarr. This is done in the second notebook: [2_convert_nwm_predictions_to_zarr][3]. The converted Zarr files are saved in an Azavea bucket `azavea-noaa-hydro-data`, and done via Dask to achieve parallalism. The conversion for 24 hours of predictions takes about 17 minutes.

Once the Zarr files are available, we run the same analysis as before in the third notebook: [3_evaluating_nwm_streamflow_predictions_zarr][4], with the only difference being in the _Fetch the NWM Short Range Forecast_ block, which uses the Zarr files.

## Doing the Analysis using Kerchunk

Creating the Zarr files is expensive and redundant: it requires that all the existing data be converted into a new format, and also that the same data be saved twice, just in different formats. A much better alternative is [Kerchunk][5], which creates a metadata JSON file that allows the Zarr engine to read NetCDF files.

We create these metadata JSON files, one per NetCDF file, in the fourth notebook: [4_convert_nwm_predictions_to_kerchunk_single][6]. The JSON files are saved in the Azavea bucket `azavea-noaa-hydro-data`, but the original data stays in the `noaa-nwm-pds` bucket. This operation is not redundant, and is also very quick, taking about 30 seconds.

Once the Kerchunk files are available, we run the same analysis as before in the fifth notebook: [5_evaluating_nwm_streamflow_predictions_kerchunk][7], with the key difference again being in the _Fetch the NWM Short Range Forecast_ block, which uses the Kerchunk files.

## Comparison

All of these notebooks were executed on Azavea's JupyterHub installation, which run on `r5.xlarge` pods. These have 4 CPU cores, 32GB of RAM, and have proximity to the S3 buckets given that they are running on AWS, thus can transfer data at very high speeds ~100Mbps.

This is a table of the time different blocks took to execute:

| Block                                        | NetCDF | Zarr   | Kerchunk |
|----------------------------------------------|--------|--------|----------|
| Fetch the NWM Short Range Forecast           | 1m 55s | 5m 57s | 1m 46s   |
| Pick a single feature to analyze             | 25s    | 2m 26s | 36s      |
| Average deviation for every reach in the HUC | 2m 51s | 4m 28s | 3m 4s    |

Here's the peak RAM use and total network transfer in each case:

|                     | NetCDF  | Zarr    | Kerchunk |
|---------------------|---------|---------|----------|
| Total Data Transfer | 2.13 GB | 2.71 GB | 1.97 GB  |
| Peak RAM Usage      | 8 GB    | 9 GB    | 13 GB    |

We did note that network access from the `noaa-nwm-pds` bucket was much faster than that from the `azavea-noaa-hydro-data` bucket, which likely contributes the extra time observed for the Zarr case which fetches all its data from the latter. If this discrepancy is fixed, the above tables will be updated with new values.

## Conclusion

As observed from the tables above, both Zarr and Kerchunk use extra resources and do not offer significant speed up or lower resource utilization compared to reading the original NetCDF files. This, combined with the fact that the recency of data is very valuable when it comes to forecast, accessing the source files directly is preferable to a transformed version which adds processing time.


[1]: https://water.noaa.gov/about/output_file_contents
[2]: ./1_evaluating_nwm_streamflow_predictions_netcdf.ipynb
[3]: ./2_convert_nwm_predictions_to_zarr.ipynb
[4]: ./3_evaluating_nwm_streamflow_predictions_zarr.ipynb
[5]: https://github.com/fsspec/kerchunk
[6]: ./4_convert_nwm_predictions_to_kerchunk_single.ipynb
[7]: ./5_evaluating_nwm_streamflow_predictions_kerchunk.ipynb