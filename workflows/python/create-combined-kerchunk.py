from argparse import ArgumentParser
import json
from kerchunk.combine import MultiZarrToZarr
import s3fs
from typing import Callable, List, Optional
from urllib.parse import urlparse

def find_forecasts(
    fs: s3fs.S3FileSystem,
    base_url: str,
    forecast_duration: str="short_range",
    forecast_type: str="channel_rt",
    file_type: str="nc"
) -> List[str]:
    parsed = urlparse(base_url)
    base = "/".join([pth for pth in [parsed.netloc, parsed.path[1:]] if pth != ""])
    print(base)
    folders = list(filter(
        lambda path: path.startswith("nwm."),
        map(lambda path: path.split("/")[len(base.split("/"))], fs.glob(f"s3://{base}/*"))
    ))
    forecasts = [path for folder in folders for path in fs.glob(f"s3://{base}/{folder}/{forecast_duration}/*{forecast_type}*.{file_type}")]
    return forecasts

def main(json_base_url, combined_kerchunk_url):
    fs = s3fs.S3FileSystem()
    single_json_file_list = find_forecasts(
        fs,
        json_base_url,
        file_type="json"
    )

    kerchunks = []
    for ref in single_json_file_list:
       with fs.open(ref, mode='r') as f:
           kerchunks.append(json.load(f))

    mzz = MultiZarrToZarr(
        kerchunks,
        remote_protocol='s3', remote_options={'anon': True},
        concat_dims=['reference_time', 'time']
    )
    combined = mzz.translate()

    with fs.open(combined_kerchunk_url, mode='wb') as outfile:
        outfile.write(json.dumps(combined).encode())

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("json_store_url", metavar="<src_uri>", type=str, help="The base URI of the individual Kerchunk storage")
    parser.add_argument("kerchunk_path", metavar="<dest>", type=str, help="The destination URL for the combined Kerchunk file")
    args = parser.parse_args()
    main(
        args.json_store_url.rstrip('/'),
        args.kerchunk_path
    )
