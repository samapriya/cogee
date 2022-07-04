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
import logging
import os
import json
import webbrowser
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

# Go to the readMe


def account():
    try:
        a = webbrowser.open(
            "https://signup.earthengine.google.com/#!/service_accounts", new=2)
        if a == False:
            print("Your setup does not have a monitor to display the webpage")
    except Exception as e:
        print(e)


def account_from_parser(args):
    account()


def register(bucket_name, prefix, collection_path, cred, account):
    if cred and account is not None:
        credentials = ee.ServiceAccountCredentials(account, cred)
        ee.Initialize(credentials)
    else:
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
    storage_client = storage.Client()
    if prefix is None:
        blobs = storage_client.list_blobs(
            bucket_name, prefix="")
        gcs_asset_list = [blob.name.split('.tif')[0]
                          for blob in blobs if len(blob.name.split('/')) == 1]
    else:
        bucket = storage_client.get_bucket(bucket_name)
        blobs_specific = list(bucket.list_blobs(
            prefix=prefix))
        gcs_asset_list = [blob.name.split('.tif')[0]
                          for blob in blobs_specific]
    assets_list = ee.data.getList(params={"id": collection_path})
    gee_asset_list = [os.path.basename(asset["id"]) for asset in assets_list]
    bucket_list = [asset.split('/')[-1] for asset in gcs_asset_list]
    remaining_items = set(bucket_list)-set(gee_asset_list)
    if len(remaining_items) > 0:
        for i, object in enumerate(list(remaining_items)):
            asset_id = object
            asset_id_img = f"{collection_path}/{asset_id.split('/')[-1]}"
            start_date = datetime.strptime(asset_id.split('_')[-3], '%Y%m%d')
            tile_id = asset_id.split('_')[-2]
            start_date = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            if prefix is None:
                uri = f"gs://{bucket_name}/{asset_id}.tif"
            else:
                uri = f"gs://{bucket_name}/{prefix}/{asset_id}.tif"
            cog_manifest = {
                "type": "IMAGE",
                "gcs_location": {
                        "uris": [uri]
                }, 'properties': {
                    'tile_id': tile_id
                },
                "startTime": start_date,
                "endTime": start_date
            }
            try:
                if ee.data.getAsset(asset_id_img):
                    print(f"Asset {asset_id_img} already exists: SKIPPING")
            except Exception:
                logging.info(
                    f"Ingesting {i+1} of {len(remaining_items)}: {asset_id_img} to {collection_path}")
                try:
                    ee.data.createAsset(cog_manifest, asset_id_img)
                except Exception as error:
                    print(
                        f'Failed to ingest {asset_id_img} to {collection_path}')
            except (KeyboardInterrupt, SystemExit) as error:
                sys.exit("Program escaped by User")
    elif len(remaining_items) == 0:
        print('All images already exists in collection')


def register_from_parser(args):
    register(bucket_name=args.bucket, prefix=args.prefix,
             collection_path=args.collection)


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

    parser_account = subparsers.add_parser(
        "account", help="Setup/Register Google Service account for use with GEE"
    )
    parser_account.set_defaults(func=account_from_parser)

    parser_buckets = subparsers.add_parser(
        "buckets", help="Lists all Google Cloud Project buckets"
    )
    parser_buckets.set_defaults(func=buckets_from_parser)

    parser_register = subparsers.add_parser(
        "register", help="Register COGs to GEE collection"
    )
    required_named = parser_register.add_argument_group(
        "Required named arguments.")
    required_named.add_argument(
        "--bucket", help="Google Cloud Project bucket name", required=True)
    required_named.add_argument(
        "--collection", help="GEE collection path", required=True)
    optional_named = parser_register.add_argument_group(
        "Optional named arguments")
    optional_named.add_argument(
        "--prefix", help="path/to/subfolder/",
        default=None,
    )
    optional_named.add_argument(
        "--cred", help="Path to Credentials.JSON file for service account",
        default=None,
    )
    optional_named.add_argument(
        "--account", help="Service account email address",
        default=None,
    )
    parser_register.set_defaults(func=register_from_parser)

    args = parser.parse_args()

    try:
        func = args.func
    except AttributeError:
        parser.error("too few arguments")
    func(args)


if __name__ == "__main__":
    main()
