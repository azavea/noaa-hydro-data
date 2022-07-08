#!/usr/bin/env python
# coding: utf-8

# # Save HUC2 02 COMIDs to a JSON file on S3
# 
# These will be used to create a subset of NWM for testing purposes.

import json
from os.path import basename, join

from smart_open import open as smart_open
import boto3
from tqdm import tqdm

# Code from https://alexwlchan.net/2017/07/listing-s3-keys/
def get_matching_s3_objects(bucket, prefix='', suffix='',
                            request_payer='None'):
    """
    Generate objects in an S3 bucket.
    :param bucket: Name of the S3 bucket.
    :param prefix: Only fetch objects whose key starts with
        this prefix (optional).
    :param suffix: Only fetch objects whose keys end with
        this suffix (optional).
    """
    s3 = boto3.client('s3')
    kwargs = {'Bucket': bucket, 'RequestPayer': request_payer}

    # If the prefix is a single string (not a tuple of strings), we can
    # do the filtering directly in the S3 API.
    if isinstance(prefix, str):
        kwargs['Prefix'] = prefix

    while True:

        # The S3 API response is a large blob of metadata.
        # 'Contents' contains information about the listed objects.
        resp = s3.list_objects_v2(**kwargs)

        try:
            contents = resp['Contents']
        except KeyError:
            return

        for obj in contents:
            key = obj['Key']
            if key.startswith(prefix) and key.endswith(suffix):
                yield obj

        # The S3 API is paginated, returning up to 1000 keys at a time.
        # Pass the continuation token into the next response, until we
        # reach the final page (when this field is missing).
        try:
            kwargs['ContinuationToken'] = resp['NextContinuationToken']
        except KeyError:
            break

def get_json(uri):
    with smart_open(uri) as fd:
        return json.load(fd)

def save_json(json_dict, uri):
    with smart_open(uri, 'w') as fd:
        json.dump(json_dict, fd)


# get all huc8 extract files on s3 with 02 in prefix.
# this is the set that lies within huc2 02 (which is in themid-atlantic region)

huc8_root_uri = 's3://azavea-noaa-hydro-data/noaa/huc8-extracts/transformed/'
huc8_fns = [
    basename(x['Key'])
    for x in list(get_matching_s3_objects('azavea-noaa-hydro-data', 'noaa/huc8-extracts/transformed/02', 'json'))]

reach_ids = []
for huc8_fn in tqdm(huc8_fns):
    huc8_dict = get_json(join(huc8_root_uri, huc8_fn))
    reach_ids.extend(huc8_dict['features'][0]['properties']['comids'])

reach_ids.sort()


out_uri = 's3://azavea-noaa-hydro-data/noaa/huc2-comids.json'
save_json({'comids': reach_ids}, out_uri)

