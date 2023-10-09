from argparse import ArgumentParser
from datetime import datetime, timedelta
from functools import partial
import os
import s3fs
from typing import cast, Callable, List, Optional
from urllib.parse import urlparse

def find_forecasts(
  base_url: str,
  forecast_duration: str="short_range",
  forecast_type: str="channel_rt",
  file_type: str="nc",
  folder_filter: Optional[Callable[[List[str]], List[str]]]=None
) -> List[str]:
  fs = s3fs.S3FileSystem()
  parsed = urlparse(base_url)
  base = "/".join([pth for pth in [parsed.netloc, parsed.path[1:]] if pth != ""])
  print(base)
  folders = cast(List[str], list(filter(
    lambda path: path.startswith("nwm."),
    map(lambda path: path.split("/")[len(base.split("/"))], fs.glob(f"s3://{base}/*"))
  )))
  if folder_filter is not None:
    folders = folder_filter(folders)
  forecasts = [path for folder in folders for path in fs.glob(f"s3://{base}/{folder}/{forecast_duration}/*{forecast_type}*.{file_type}")]
  return forecasts

def keep_n_days(n: int, original_folders: List[str]) -> List[str]:
  oldest_date = datetime.strptime(sorted(original_folders)[-1].split(".")[1], "%Y%m%d")
  threshold = oldest_date - timedelta(days=n)
  return list(filter(
    lambda folder: datetime.strptime(folder.split(".")[1], "%Y%m%d") >= threshold,
    original_folders
  ))

def index_from_path(p: str):
  trimmed = p[:p.rfind('.')]
  return "/".join(trimmed.split("/")[-3:])


def main(source_path, intermed_path, dest_path, n_days=None):
  filtered_noaa_forecasts = find_forecasts(
    source_path,
    folder_filter=partial(keep_n_days, n_days) if n_days is not None else None
  )
  all_existing_jsons = find_forecasts(
    intermed_path,
    file_type="json"
  )

  source_keys = set(map(index_from_path, filtered_noaa_forecasts))
  destination_keys = set(map(index_from_path, all_existing_jsons))

  to_create = list(filter(
    lambda f: index_from_path(f) not in destination_keys,
    filtered_noaa_forecasts
  ))
  to_delete = list(filter(
    lambda f: index_from_path(f) not in source_keys,
    all_existing_jsons
  ))

  print({
    "num-new": len(to_create),
    "num-stale": len(to_delete)
  })

  with open(os.path.join(dest_path, "new-files.txt"), "w") as f:
    f.write('\n'.join(to_create))
  with open(os.path.join(dest_path, "stale-files.txt"), "w") as f:
    f.write('\n'.join(to_delete))
  with open(os.path.join(dest_path, "new-count.txt"), "w") as f:
    f.write(str(len(to_create)))
  with open(os.path.join(dest_path, "stale-count.txt"), "w") as f:
    f.write(str(len(to_delete)))

if __name__ == "__main__":
  parser = ArgumentParser()
  parser.add_argument("-n", "--keep-n-days", dest="keep_n_days", type=int, default=None)
  parser.add_argument("-o", "--output", dest="output_path", type=str, default="/tmp")
  parser.add_argument("source_path", metavar="<src>", type=str, help="The source directory containing the raw NWM NetCDF files")
  parser.add_argument("kerchunk_path", metavar="<dest>", type=str, help="The destination directory containing intermediate (individual) Kerchunk files")
  args = parser.parse_args()
  main(
    args.source_path.rstrip('/'),
    args.kerchunk_path.rstrip('/'),
    args.output_path,
    n_days=args.keep_n_days
  )
