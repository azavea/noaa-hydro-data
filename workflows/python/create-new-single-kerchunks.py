import argparse, json, os, s3fs
from urllib.parse import urlparse
from kerchunk.hdf import SingleHdf5ToZarr

def generate_kerchunk(s3_client, netcdf_path, store_url):
    with s3_client.open(netcdf_path, mode='rb', anon=True) as ncfile:
        out_prefix = urlparse(netcdf_path).path[1:]
        json_url = f'{store_url}/{out_prefix[:-3]}.json'
        with s3_client.open(json_url, mode='wb') as outfile:
            print(f"Writing to {json_url}")
            outfile.write(
                json.dumps(
                    SingleHdf5ToZarr(ncfile, netcdf_path).translate()
                ).encode()
            )
            return json_url

def main(input_path, store_url):
  with open(os.path.join(input_path, "new-files.txt")) as f:
      files = f.readlines()
      print(f"Seeing {len(files)} new netcdf files")

  fs = s3fs.S3FileSystem()
  for filename in files:
      filename = f"s3://{filename.strip()}"
      try:
          generate_kerchunk(fs, filename, store_url)
      except FileNotFoundError as e:
          print(f"Did not find {filename}!  Exception was {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", dest="input_path", type=str, default="/tmp")
    parser.add_argument("kerchunk_path", metavar="<dest>", type=str, help="The destination URL containing intermediate (individual) Kerchunk files")
    args = parser.parse_args()
    main(
        args.input_path,
        args.kerchunk_path.rstrip('/')
    )
