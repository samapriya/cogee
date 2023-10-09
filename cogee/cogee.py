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
import webbrowser
from datetime import datetime

import ee
import google
import pkg_resources
import requests
from bs4 import BeautifulSoup
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

logging.basicConfig(
    format="%(asctime)s %(levelname)-4s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

class Solution:
    """
    A class for comparing version strings.
    """

    def compareVersion(self, version1, version2):
        """
        Compare two version strings.

        Args:
            version1 (str): The first version string.
            version2 (str): The second version string.

        Returns:
            int: 1 if version1 > version2, -1 if version1 < version2, 0 if equal.
        """
        versions1 = [int(v) for v in version1.split(".")]
        versions2 = [int(v) for v in version2.split(".")]
        for i in range(max(len(versions1), len(versions2))):
            v1 = versions1[i] if i < len(versions1) else 0
            v2 = versions2[i] if i < len(versions2) else 0
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1
        return 0


ob1 = Solution()


def cogee_version():
    """
    Check and notify about the latest version of the 'cogee' package.
    """
    url = "https://pypi.org/project/cogee/"
    source = requests.get(url)
    html_content = source.text
    soup = BeautifulSoup(html_content, "html.parser")
    company = soup.find("h1")
    vcheck = ob1.compareVersion(
        company.string.strip().split(" ")[-1],
        pkg_resources.get_distribution("cogee").version,
    )
    if vcheck == 1:
        print(
            f"Current version of cogee is {pkg_resources.get_distribution('cogee').version} upgrade to latest version: {company.string.strip().split(' ')[-1]}"
        )
    elif vcheck == -1:
        print(
            f"Possibly running staging code {pkg_resources.get_distribution('cogee').version} compared to pypi release {company.string.strip().split(' ')[-1]}"
        )

cogee_version()

# Go to the readMe
def readme():
    try:
        a = webbrowser.open(
            "https://cogee.geetools.xyz", new=2
        )
        if a == False:
            print("Your setup does not have a monitor to display the webpage")
            print(
                " Go to {}".format(
                    "https://cogee.geetools.xyz"
                )
            )
    except Exception as e:
        print(e)

def read_from_parser(args):
    readme()

def init(project):
    """
    Initialize and authenticate with Google Earth Engine.

    Args:
        project (str): The name of the Google Cloud Platform project.

    This function performs the following steps:
    1. Prints a message indicating the start of the Earth Engine initialization process.
    2. Specifies the OAuth 2.0 authentication scopes required for Earth Engine access.
    3. Retrieves the Google Cloud Platform credentials and project ID associated with the specified scopes.
    4. Initializes the Earth Engine client using the obtained credentials and the specified project name.

    Note: Make sure the necessary Google Cloud Platform and Earth Engine libraries are imported before calling this function.
    """
    try:
        logging.info("Logging into Google Cloud Project & initializing Earth Engine")

        # Define the authentication scopes required for Earth Engine access
        SCOPES = [
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/earthengine",
        ]

        # Retrieve Google Cloud Platform credentials and project ID
        CREDENTIALS, project_id = google.auth.default(default_scopes=SCOPES)

        # Initialize the Earth Engine client with the obtained credentials and project name
        ee.Initialize(CREDENTIALS, project=project)
        logging.info(f'Initialization complete')
    except Exception as error:
        logging.error(f'Initialization failed with error {error}')


def init_from_parser(args):
    init(project=args.project)


# Function to register your Earth Engine service account if not registered
def ee_sa():
    # Define the URL where users can register their Earth Engine service account
    url = "https://signup.earthengine.google.com/#!/service_accounts"

    try:
        # Attempt to open the URL in a web browser (new=2 means open in a new tab/window)
        a = webbrowser.open(url, new=2)

        # Check if the web browser was successfully opened
        if a == False:
            logging.info("Your setup does not have a monitor to display the webpage")
            logging.info(f"Go to {url} to register your service account")
    except Exception as e:
        # Handle any exceptions that may occur during the process
        logging.exception(e)


def ee_sa_from_parser(args):
    ee_sa()



# def bucket_list():
#     storage_client = storage.Client()
#     for bucket in storage_client.list_buckets():
#         print(bucket.name)

def list_buckets(project_id):
    """
    List and print the names of all buckets associated with a Google Cloud project.

    Args:
        project_id (str): The ID of the Google Cloud project containing the buckets.

    Returns:
        list of str: A list of bucket names.
    """
    try:
        # Initialize a Google Cloud Storage client
        if project_id is not None:
            storage_client = storage.Client(project=project_id)
        else:
            storage_client = storage.Client()
        # List and print the names of all buckets in the project
        bucket_names = [bucket.name for bucket in storage_client.list_buckets()]
        if bucket_names:
            for bucket_name in bucket_names:
                print(bucket_name)
        else:
            print("No buckets found or an error occurred.")
        return bucket_names
    except GoogleCloudError as e:
        # Handle Google Cloud errors
        print(f"Google Cloud Error: {e}")
        return []
    except Exception as e:
        # Handle other exceptions
        print(f"An error occurred: {e}")
        return []

def buckets_from_parser(args):
    list_buckets(project_id=args.pid)


def list_tif(bucket_name, prefix, limit):
    """
    List Cloud Storage objects with a specified prefix and filter by file extension.

    Args:
        bucket_name (str): The name of the Cloud Storage bucket.
        prefix (str, optional): Prefix for filtering objects within the bucket.
        limit (int, optional): Maximum number of results to return.

    Returns:
        list: List of dictionaries containing properties of matching .tif files.
    """
    storage_client = storage.Client()
    if limit is not None:
        blobs = storage_client.list_blobs(
            bucket_name, prefix=prefix, max_results=int(limit)
        )
    else:
        blobs = storage_client.list_blobs(
            bucket_name, prefix=prefix
        )
    tif_files = []

    for blob in blobs:
        if blob.name.lower().endswith(".tif"):
            properties = {
                "name": blob.name,
                "time_created": blob.time_created.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "time_updated": blob.updated.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "file_size_bytes": blob.size,
            }
            tif_files.append(properties)
    return tif_files


def subfolders(bucket_name):
    """
    List subfolders within a Cloud Storage bucket.

    Args:
        bucket_name (str): The name of the Cloud Storage bucket.
    Returns:
        list: List of subfolder names.
    """
    storage_client = storage.Client()
    subfolders = set()
    prefix = ""

    try:
        logging.info(f"Fetching subfolders/prefixes in bucket {bucket_name}")
        blobs = storage_client.list_blobs(bucket_name, prefix="")

        for blob in blobs:
            relative_path = blob.name[len(prefix):]
            parts = relative_path.split("/")

            if len(parts) > 1:
                subfolders.add(parts[0])

        print(json.dumps(list(subfolders),indent=2))
    except Exception as error:
        logging.error(f"Failed to fetch subfolders with error: {error}")
        return []

def subfolders_from_parser(args):
    subfolders(bucket_name=args.bucket)


def get_property(data_list, target_name):
    matching_dicts = []

    for item in data_list:
        if "name" in item and target_name.lower() in item["name"].lower():
            matching_dicts.append(item)

    return matching_dicts


def register(bucket_name, prefix, collection_path, cred, account, limit):
    if cred and account is not None:
        credentials = ee.ServiceAccountCredentials(account, cred)
        ee.Initialize(credentials)
    else:
        ee.Initialize()
    try:
        if ee.data.getAsset(collection_path):
            print(
                "Collection exists: {}".format(ee.data.getAsset(collection_path)["id"])
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
    ptif = list_tif(bucket_name, prefix, limit)
    gcs_asset_list = [file.get("name").split("/")[-1].split(".tif")[0] for file in ptif]
    remaining_items = set(gcs_asset_list) - set(gee_asset_list)
    print(f"Items left to register: {len(remaining_items)}")
    if len(remaining_items) > 0:
        for i, object in enumerate(list(remaining_items)):
            asset_id = get_property(ptif, object)[0]
            asset_id_img = (
                f"{collection_path}/{asset_id.get('name').split('/')[-1].split('.')[0]}"
            )
            created_date = asset_id.get("time_created")
            updated_date = asset_id.get("time_updated")
            file_size_bytes = asset_id.get("file_size_bytes")
            # print(asset_id_img,created_date,file_size_bytes)
            # tile_id = asset_id.split('_')[-2]
            # start_date = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            if prefix is None:
                uri = f"gs://{bucket_name}/{asset_id.get('name')}"
            else:
                uri = f"gs://{bucket_name}/{prefix}/{asset_id.get('name')}"
            cog_manifest = {
                "type": "IMAGE",
                "gcs_location": {"uris": [uri]},
                "properties": {"file_size_bytes": file_size_bytes},
                "startTime": created_date,
                "endTime": updated_date,
            }
            # print(json.dumps(cog_manifest))
            try:
                if ee.data.getInfo(asset_id_img) is not None:
                    print(f"Asset {asset_id_img} already exists: SKIPPING")
                else:
                    try:
                        register = ee.data.createAsset(cog_manifest, asset_id_img)
                        if register.get("id") is not None:
                            logging.info(
                                f"Registered {i+1} of {len(remaining_items)}: {asset_id_img} to {collection_path}"
                            )
                    except Exception as error:
                        print(
                            f"Failed to register {asset_id_img} to {collection_path} with error {error}"
                        )
            except ee.ee_exception.EEException:
                print(f"Failed to register {asset_id_img} to {collection_path}")
            except (KeyboardInterrupt, SystemExit) as error:
                sys.exit("Program escaped by User")
    elif len(remaining_items) == 0:
        print("All images already exists in collection")


def register_from_parser(args):
    register(
        bucket_name=args.bucket,
        prefix=args.prefix,
        collection_path=args.collection,
        limit=args.limit,
        cred=args.cred,
        account=args.account,
    )


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Simple CLI for COG registration to GEE"
    )
    subparsers = parser.add_subparsers()

    parser_read = subparsers.add_parser(
        "readme", help="Go the web based cogee readme page"
    )
    parser_read.set_defaults(func=read_from_parser)

    parser_init = subparsers.add_parser("init", help="GEE project auth")
    required_named = parser_init.add_argument_group("Required named arguments.")
    required_named.add_argument(
        "--project", help="Google Cloud Project name", required=True
    )
    parser_init.set_defaults(func=init_from_parser)

    parser_ee_sa = subparsers.add_parser(
        "account", help="Setup/Register Google Service account for use with GEE"
    )
    parser_ee_sa.set_defaults(func=ee_sa_from_parser)

    parser_buckets = subparsers.add_parser(
        "buckets", help="Lists all Google Cloud Project buckets"
    )
    optional_named = parser_buckets.add_argument_group("Optional named arguments")
    optional_named.add_argument("--pid", help="Google Project ID", default=None)
    parser_buckets.set_defaults(func=buckets_from_parser)

    parser_subfolders = subparsers.add_parser(
        "recursive", help="Prints subfolder or prefix names in a bucket"
    )
    required_named = parser_subfolders.add_argument_group("Required named arguments.")
    required_named.add_argument(
        "--bucket", help="Google Cloud Project bucket name", required=True
    )
    parser_subfolders.set_defaults(func=subfolders_from_parser)

    parser_register = subparsers.add_parser(
        "register", help="Register COGs to GEE collection"
    )
    required_named = parser_register.add_argument_group("Required named arguments.")
    required_named.add_argument(
        "--bucket", help="Google Cloud Project bucket name", required=True
    )
    optional_named = parser_register.add_argument_group("Optional named arguments")
    optional_named.add_argument("--prefix", help="subfolder", default=None)
    optional_named.add_argument(
        "--limit", help="Max number of assets to register", default=None
    )
    optional_named.add_argument(
        "--cred",
        help="Path to Credentials.JSON file for service account",
        default=None,
    )
    optional_named.add_argument(
        "--account",
        help="Service account email address",
        default=None,
    )
    required_named.add_argument(
        "--collection", help="GEE collection path", required=True
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
