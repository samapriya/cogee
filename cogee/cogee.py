__copyright__ = """
    Copyright 2022 Samapriya Roy
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at
       http://www.apache.org/licenses/LICENSE-2.0
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
__license__ = "Apache 2.0"

import argparse
import json
import logging
import os
import sys
from datetime import datetime

import ee
import google
from google.cloud import storage

logging.basicConfig(
    format="%(asctime)s %(levelname)-4s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def init(pname):
    print("Logging into Earth Engine")
    SCOPES = ['https://www.googleapis.com/auth/cloud-platform',
              'https://www.googleapis.com/auth/earthengine']
    CREDENTIALS, project_id = google.auth.default(default_scopes=SCOPES)
    ee.Initialize(CREDENTIALS, project=pname)


def init_from_parser(args):
    init(pname=args.project)


def bucket_list():
    storage_client = storage.Client()
    for bucket in storage_client.list_buckets():
        print(bucket.name)


def buckets_from_parser(args):
    bucket_list()

def list_tif(bucket_name, prefix,limit):
    storage_client = storage.Client()
    blobs = storage_client.list_blobs(bucket_name, prefix=prefix,max_results=int(limit))

    tif_files = []

    for blob in blobs:
        if blob.name.lower().endswith(".tif"):
            properties = {
                "name": blob.name,
                "time_created": blob.time_created.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "file_size_bytes": blob.size
            }
            tif_files.append(properties)
    return tif_files


def subfolders(bucket_name):
    prefix = ""
    storage_client = storage.Client()
    subfolders = set()
    blobs = storage_client.list_blobs(bucket_name, prefix="")
    for blob in blobs:
        relative_path = blob.name[len(prefix):]
        parts = relative_path.split("/")
        if len(parts) > 1:
            subfolders.add(parts[0])
    print(json.dumps(list(subfolders),indent=2))

def subfolders_from_parser(args):
    subfolders(bucket_name=args.bucket)

def get_property(data_list, target_name):
    matching_dicts = []

    for item in data_list:
        if "name" in item and target_name.lower() in item["name"].lower():
            matching_dicts.append(item)

    return matching_dicts

def register(bucket_name, prefix, collection_path,limit):
    ee.Initialize()
    try:
        if ee.data.getAsset(collection_path):
            print(
                "Collection exists: {}".format(
                    ee.data.getAsset(collection_path)["id"])
            )
    except Exception:
        print("Collection does not exist: Creating {}".format(collection_path))
        try:
            ee.data.createAsset(
                {"type": ee.data.ASSET_TYPE_IMAGE_COLL_CLOUD}, collection_path
            )
        except Exception:
            ee.data.createAsset(
                {"type": ee.data.ASSET_TYPE_IMAGE_COLL}, collection_path
            )
    assets_list = ee.data.getList(params={"id": collection_path})
    gee_asset_list = [os.path.basename(asset["id"]) for asset in assets_list]
    ptif = list_tif(bucket_name, prefix,limit)
    gcs_asset_list = [file.get('name').split('/')[-1].split('.tif')[0] for file in ptif]
    remaining_items = set(gcs_asset_list)-set(gee_asset_list)
    print(f'Items left to register: {len(remaining_items)}')
    if len(remaining_items) > 0:
        for i, object in enumerate(list(remaining_items)):
            asset_id = get_property(ptif, object)[0]
            asset_id_img = f"{collection_path}/{asset_id.get('name').split('/')[-1].split('.')[0]}"
            created_date = asset_id.get('time_created')
            file_size_bytes = asset_id.get('file_size_bytes')
            #print(asset_id_img,created_date,file_size_bytes)
            # tile_id = asset_id.split('_')[-2]
            # start_date = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            if prefix is None:
                uri = f"gs://{bucket_name}/{asset_id.get('name')}"
            else:
                uri = f"gs://{bucket_name}/{prefix}/{asset_id.get('name')}"
            cog_manifest = {
                "type": "IMAGE",
                "gcs_location": {
                        "uris": [uri]
                }, 'properties': {
                    'file_size_bytes': file_size_bytes
                },
                "startTime": created_date,
                "endTime": created_date
            }
            #print(json.dumps(cog_manifest))
            try:
                if ee.data.getInfo(asset_id_img) is not None:
                    print(f"Asset {asset_id_img} already exists: SKIPPING")
                else:
                    logging.info(
                        f"Registering {i+1} of {len(remaining_items)}: {asset_id_img} to {collection_path}")
                    try:
                        register = ee.data.createAsset(cog_manifest, asset_id_img)
                        #print(json.dumps(register, indent=2))
                    except Exception as error:
                        print(
                            f'Failed to register {asset_id_img} to {collection_path} with error {error}')
            except ee.ee_exception.EEException:
                print(f'Failed to register {asset_id_img} to {collection_path}')
            except (KeyboardInterrupt, SystemExit) as error:
                sys.exit("Program escaped by User")
    elif len(remaining_items) == 0:
        print('All images already exists in collection')


def register_from_parser(args):
    register(bucket_name=args.bucket, prefix=args.prefix,
             collection_path=args.collection,limit=args.limit)


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Simple CLI for COG registration to GEE")
    subparsers = parser.add_subparsers()

    parser_init = subparsers.add_parser(
        "init", help="GEE project auth"
    )
    required_named = parser_init.add_argument_group(
        "Required named arguments.")
    required_named.add_argument(
        "--project", help="Google Cloud Project name", required=True)
    parser_init.set_defaults(func=init_from_parser)

    parser_buckets = subparsers.add_parser(
        "buckets", help="Lists all Google Cloud Project buckets"
    )
    parser_buckets.set_defaults(func=buckets_from_parser)

    parser_subfolders = subparsers.add_parser(
        "subfolder", help="Prints subfolder or prefix names"
    )
    required_named = parser_subfolders.add_argument_group(
        "Required named arguments.")
    required_named.add_argument(
        "--bucket", help="Google Cloud Project bucket name", required=True)
    parser_subfolders.set_defaults(func=subfolders_from_parser)


    parser_register = subparsers.add_parser(
        "register", help="Register COGs to GEE collection"
    )
    required_named = parser_register.add_argument_group(
        "Required named arguments.")
    required_named.add_argument(
        "--bucket", help="Google Cloud Project bucket name", required=True)
    optional_named = parser_register.add_argument_group(
        "Optional named arguments")
    optional_named.add_argument(
        "--prefix", help="subfolder",
        default=None,
    )
    optional_named.add_argument(
        "--limit", help="subfolder",
        default=None,
    )
    required_named.add_argument(
        "--collection", help="GEE collection path", required=True)
    parser_register.set_defaults(func=register_from_parser)

    args = parser.parse_args()

    try:
        func = args.func
    except AttributeError:
        parser.error("too few arguments")
    func(args)


if __name__ == "__main__":
    main()
