# Evaluating NWM Streamflow Predictions

The National Water Model (NWM) Predictions Dataset contains [short range, medium range, and long range predictions][1] of various stream metrics for features across the United States. The streamflow predictions are presented as channel point files, in the NetCDF format.

The notebooks in this folder answer two questions:

  1. How does the streamflow prediction vary over time?
  2. How does such analysis done on the NetCDF files compare with the same analysis done in more cloud-friendly formats, such as Zarr or Kerchunk?

## Analyzing Change in Streamflow Predictions Over Time

This is done in the first notebook: [1_evaluating_nwm_streamflow_predictions_netcdf][2]. This picks a HUC to analyze, and fetches all the NHD streams therein. Then it fetches the NWM Predictions for a certain date, from the NetCDF files in the `noaa-nwm-pds` S3 bucket, and intersects the NWM features with the NHD comids. Once we have this subset, we analyze it. The data is opened with xarray's `xr.open_mfdataset` method, which can open a dataset spread across multiple files.

First we pick a single stream to analyze. For that stream, we look at each of the short range predictions, and chart how those predictions change over 24 hours. We graph the standard deviation per hour, and also calculate the average deviation for that stream.

Next, we take that calculation and apply it to all the streams in the HUC. We visualize this variation, observing that the main stem of a river has higher variation than the contributing streams. This makes intuitive sense, since the main stem is absorbing the variation from a large number of contributing streams, and as such has more uncertainty.

## Doing the Analysis using Zarr

The Zarr format is better for cloud querying than NetCDF. However, it requires that the input be first converted to Zarr. This is done in the second notebook: [2_convert_nwm_predictions_to_zarr][3]. The converted Zarr files are saved in an Azavea bucket `azavea-noaa-hydro-data`, and done via Dask to achieve parallalism. The conversion for 24 hours of predictions takes about 17 minutes.

Once the Zarr files are available, we run the same analysis as before in the third notebook: [3_evaluating_nwm_streamflow_predictions_zarr][4], with the only difference being in the _Fetch the NWM Short Range Forecast_ block, which uses the Zarr files.

## Doing the Analysis using Kerchunk

Creating the Zarr files is expensive and redundant: it requires that all the existing data be converted into a new format, and also that the same data be saved twice, just in different formats. A much better alternative is [Kerchunk][5], which creates a metadata JSON file that allows the Zarr engine to read NetCDF files.

We create these metadata JSON files, one per NetCDF file, in the fourth notebook: [4_convert_nwm_predictions_to_kerchunk_single][6]. The JSON files are saved in the Azavea bucket `azavea-noaa-hydro-data`, but the original data stays in the `noaa-nwm-pds` bucket. This operation is not redundant, and is also very quick, taking about 30 seconds.

Once the Kerchunk files are available, we run the same analysis as before in the fifth notebook: [5_evaluating_nwm_streamflow_predictions_kerchunk][7], with the key difference again being in the _Fetch the NWM Short Range Forecast_ block, which uses the Kerchunk files.

## Doing the Analysis using a Combined Kerchunk file

In the above case, with multiple JSON files for the dataset, it takes a long time to open them. It is much better to combine them using [Kerchunk's `MultiZarrToZarr` capability][8] into a single file, as done in the sixth notebook: [6_convert_nwm_predictions_to_kerchunk_combined][9], and took about 4 seconds. The combined file is saved to S3, and read in the seventh notebook: [7_evaluating_nwm_streamflow_predictions_kerchunk-combined][10].

A key difference with this notebook is that because it reads from a single file, we use `xr.open_dataset` instead of `xr.open_mfdataset`. This allows for lazy reads, shifting most of the processing to happen later in the workflow when the data is actually used, rather than when the files are opened.

## Comparison

All of these notebooks were executed on Azavea's JupyterHub installation, which run on `r5.xlarge` pods. These have 4 CPU cores, 32GB of RAM, and have proximity to the S3 buckets given that they are running on AWS, thus can transfer data at very high speeds ~100Mbps.

This is a table of the time different blocks took to execute:

| Block                                                 | NetCDF | Zarr | Kerchunk | Kerchunk Combined |
| ----------------------------------------------------- | ------ | ---- | -------- | ----------------- |
| Fetch the NWM Short Range Forecast                    | 56s    | 42s  | 50s      | 381ms             |
| Subset the dataset to only the streams within the HUC | 57s    | 60s  | 1m 15s   | 321ms             |
| Average deviation for every reach in the HUC          | 945ms  | 1s   | 1.2s     | 24s               |

Here's the peak RAM use and total network transfer in each case:

|                     | NetCDF  | Zarr    | Kerchunk | Kerchunk Combined |
| ------------------- | ------- | ------- | -------- | ----------------- |
| Total Data Transfer | 2.14 GB | 1.54 GB | 1.1 GB   | 1.74 GB           |
| Peak RAM Usage      | 12 GB   | 9 GB    | 10 GB    | 750 MB            |

Here's the file size of the additional files generated, and the time it took:

|                           | NetCDF | Zarr | Kerchunk | Kerchunk Combined |
| ------------------------- | ------ | ---- | -------- | ----------------- |
| Additional Data File Size | 0      | 8 GB | 0        | 0                 |
| Metadata File Size        | 0      | 0    | 5 MB     | 5 MB + 356 KB     |
| Time to Generate          | 0      | 17m  | 30s      | 30s + 4s          |

## Conclusion

The analysis time between NetCDF, Zarr, and Kerchunk access is roughly the same. The data transfer involved is lower in Kerchunk and Zarr than in NetCDF. The RAM usage is also comparable. Converting to Zarr creates a a lot of additional data, where Kerchunk creates a very small metadata file.

In addition, when using the Kerchunk Combined variation, we see RAM usage dip to very low levels, adn the overall processing speed up a lot. Given its low resource use and low overhead, this is the recommended approach.

We have taken the Kerchunk Combined approach above and formalized it into an Argo Workflow in [#132](https://github.com/azavea/noaa-hydro-data/pull/132). This workflow produces a Kerchunk Combined index file for all the currently available NWM Predictions, allowing for fast querying of data. This combined index is created every hour and saved to AWS at `s3://azavea-noaa-hydro-data-public/nmw-combined-kerchunk.json`. A final notebook adapting the above example to this new combined index and querying 3 days of data is presented in [8_evaluating_nwm_streamflow_predictions_kerchunk-combined_via-argo][11].


[1]: https://water.noaa.gov/about/output_file_contents
[2]: ./1_evaluating_nwm_streamflow_predictions_netcdf.ipynb
[3]: ./2_convert_nwm_predictions_to_zarr.ipynb
[4]: ./3_evaluating_nwm_streamflow_predictions_zarr.ipynb
[5]: https://github.com/fsspec/kerchunk
[6]: ./4_convert_nwm_predictions_to_kerchunk_single.ipynb
[7]: ./5_evaluating_nwm_streamflow_predictions_kerchunk.ipynb
[8]: https://fsspec.github.io/kerchunk/test_example.html#multi-file-jsons
[9]: ./6_convert_nwm_predictions_to_kerchunk_combined.ipynb
[10]: ./7_evaluating_nwm_streamflow_predictions_kerchunk-combined.ipynb
[11]: ./8_evaluating_nwm_streamflow_predictions_kerchunk-combined_via-argo.ipynb