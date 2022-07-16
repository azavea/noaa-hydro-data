#!/usr/bin/env python
# coding: utf-8

# # Plot results

# ## Setup

# seaborn is not installed in notebook Docker image
get_ipython().system(' pip install seaborn')


from os.path import join
import io

import s3fs
import pandas as pd
import seaborn as sns


# Code adapted from https://stackoverflow.com/questions/63724324/saving-matplotlib-image-to-s3-bucket-from-ec2-instance
def savefig_s3(fig, out_uri, **extra_args):
    img_data = io.BytesIO()
    fig.savefig(img_data, **extra_args)
    img_data.seek(0)
    s3 = s3fs.S3FileSystem()
    with s3.open(out_uri, 'wb') as f:
        f.write(img_data.getbuffer())


def add_extra_cols(df):
    # Add chunk_sz string column for convenience.
    df['chunk_sz'] = [f'({x}, {y})' for x, y in zip(df.time_chunk_sz.values, df.feature_id_chunk_sz.values)]

    # Add human readable column names for plotting purposes. It would be nice if we didn't have to do this, and could 
    # just tell the plotting function how to translate column names.
    df['chunk shape'] = df['chunk_sz']
    df['run time: secs'] = df['time']
    df['days in query'] = df['nb_days']
    return df


out_root_uri = 's3://azavea-noaa-hydro-data/esip-experiments/plots/zarr/lf/07-16-2022a/'

# Read in results generated by benchmark_queries.ipynb.
results_uri = 's3://azavea-noaa-hydro-data/esip-experiments/benchmarks/zarr/lf/07-16-2022a.csv'
zarr_df = add_extra_cols(pd.read_csv(results_uri))
zarr_df.head()


parquet_uri = 's3://azavea-noaa-hydro-data/esip-experiments/benchmarks/parquet/lf/07-16-2022a.csv'
parquet_df = add_extra_cols(pd.read_csv(parquet_uri))
parquet_df.head()


# ## Plot using `seaborn`

# ### Make bar plot that is a visual dump of the whole dataframe.
# 
# Plotting concepts:
# * things you can control in plot: x, y, hue, row, col, 
# * independent vars: query, nb_days, chunk_sz
# * (other independent vars we aren't varying yet): data_format, nb_reaches, nb_workers
# * dependent vars: time_mean, time_std
# 
# Observations:
# * The transposed chunk size (30000, 672) is much faster for large queries over 3652 days, but doesn't have much of an effect for smaller queries.
# * The different queries all take roughly the same amount of time.

# Zarr
sns.set(font_scale = 1.2)
plot = sns.catplot(
    x='days in query', y='run time: secs', col='query', hue='chunk shape', 
    kind='bar', data=zarr_df)
fig = plot.fig
fig.subplots_adjust(top=0.85)
fig.suptitle('Timing streamflow queries using Zarr')
savefig_s3(fig, join(out_root_uri, 'zarr.png'), format='png', dpi=200)


# Parquet
plot = sns.catplot(
    x='days in query', y='run time: secs', col='query',
    kind='bar', data=parquet_df)
fig = plot.fig
fig.subplots_adjust(top=0.85)
fig.suptitle('Timing streamflow queries using Parquet')
savefig_s3(fig, join(out_root_uri, 'parquet.png'), format='png', dpi=200)


# ### Make a plot of one query comparing Zarr and Parquet

df = pd.concat([parquet_df.query('query == "mean_day"'), zarr_df.query('query == "mean_day"')])

data_format = []
for _data_format, _chunk_shape in zip(df.data_format.values, df['chunk shape'].values):
    if _data_format == 'zarr':
        data_format.append(f'zarr {_chunk_shape}')
    else:
        data_format.append('parquet')
        
df['data format'] = data_format


plot = sns.catplot(
    x='days in query', y='run time: secs', col='query', hue='data format',
    kind='bar', data=df)
fig = plot.fig
fig.subplots_adjust(top=0.85)
fig.suptitle('Comparing Zarr and Parquet for streamflow queries')
savefig_s3(fig, join(out_root_uri, 'compare.png'), format='png', dpi=200)


# ## Plot using `pandas`
# 
# (This isn't as good as using seaborn, but is here just in case).

# This groups by chunk size over all experiments to see the effect of this indpendent variable.
_df = df.groupby('chunk_sz', as_index=False).mean()
_df


_df.plot('chunk_sz', 'time_mean', 'bar')

