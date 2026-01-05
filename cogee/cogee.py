"""Google Earth Engine COG Registration Tool

SPDX-License-Identifier: Apache-2.0
"""

__license__ = "Apache 2.0"

import argparse
import importlib.metadata
import json
import logging
import os
import sys
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import ee
import google
import rasterio
import requests
from google.auth.transport.requests import AuthorizedSession
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from packaging import version as pkg_version
from rasterio.errors import RasterioIOError
from rich.console import Console
from rich.panel import Panel
from tqdm import tqdm

console = Console()

logging.basicConfig(
    format="%(asctime)s %(levelname)-4s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def compare_version(version1, version2):
    """Compare two version strings using the packaging.version module."""
    v1 = pkg_version.parse(version1)
    v2 = pkg_version.parse(version2)
    if v1 > v2:
        return 1
    elif v1 < v2:
        return -1
    else:
        return 0


def get_latest_version(package):
    """Get the latest version of a package from PyPI."""
    try:
        response = requests.get(f"https://pypi.org/pypi/{package}/json", timeout=5)
        response.raise_for_status()
        return response.json()["info"]["version"]
    except (requests.RequestException, KeyError):
        return None


def get_installed_version(package):
    """Get the installed version of a package using importlib.metadata."""
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def check_package_version(package_name):
    """Check if the installed version of a package is the latest."""
    installed_version = get_installed_version(package_name)
    latest_version = get_latest_version(package_name)

    if not installed_version or not latest_version:
        return

    result = compare_version(latest_version, installed_version)

    if result == 1:
        console.print(Panel(
            f"[yellow]Current version:[/yellow] {installed_version}\n"
            f"[green]Latest version:[/green] {latest_version}\n\n"
            f"[cyan]Upgrade with:[/cyan] pip install --upgrade {package_name}",
            title=f"[bold red]Update Available for {package_name}[/bold red]",
            border_style="red"
        ))
    elif result == -1:
        console.print(Panel(
            f"[yellow]Running staging version {installed_version}[/yellow]\n"
            f"PyPI release: {latest_version}",
            title="[bold yellow]Development Version[/bold yellow]",
            border_style="yellow"
        ))


check_package_version("cogee")


def get_sa_credentials_path():
    """Get the path to service account credentials file."""
    home = Path.home()
    sa_dir = home / ".config" / "sa_earthengine"
    sa_file = sa_dir / "sa_credentials.json"
    return sa_dir, sa_file


def get_authenticated_session():
    """
    Get an authenticated session for API requests.

    Returns:
        tuple: (session, project_name) where session is an AuthorizedSession
               and project_name is the project ID
    """
    sa_dir, sa_file = get_sa_credentials_path()

    if sa_file.exists():
        try:
            with open(sa_file) as f:
                sa_data = json.load(f)
                service_account_email = sa_data.get('client_email')

            if service_account_email:
                credentials = ee.ServiceAccountCredentials(service_account_email, str(sa_file))
                session = AuthorizedSession(credentials)
                project_name = service_account_email.split('@')[1].split('.')[0]
                return session, project_name
        except Exception:
            pass

    # Fallback to default authentication
    session = AuthorizedSession(ee.data.get_persistent_credentials())

    try:
        creds = ee.data.get_persistent_credentials()
        if hasattr(creds, 'quota_project_id') and creds.quota_project_id:
            return session, creds.quota_project_id
    except Exception:
        pass

    return session, None


def readme():
    try:
        a = webbrowser.open("https://cogee.geetools.xyz", new=2)
        if a == False:
            print("Your setup does not have a monitor to display the webpage")
            print(" Go to {}".format("https://cogee.geetools.xyz"))
    except Exception as e:
        print(e)


def read_from_parser(args):
    readme()


def init(project):
    """
    Initialize and authenticate with Google Earth Engine.

    Args:
        project (str): The name of the Google Cloud Platform project.
    """
    try:
        logging.info("Logging into Google Cloud Project & initializing Earth Engine")

        SCOPES = [
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/earthengine",
        ]

        CREDENTIALS, project_id = google.auth.default(default_scopes=SCOPES)
        ee.Initialize(CREDENTIALS, project=project)
        logging.info(f'Initialization complete')
    except Exception as error:
        logging.error(f'Initialization failed with error {error}')


def init_from_parser(args):
    init(project=args.project)


def list_buckets(project_id):
    """
    List and print the names of all buckets associated with a Google Cloud project.

    Args:
        project_id (str): The ID of the Google Cloud project containing the buckets.

    Returns:
        list of str: A list of bucket names.
    """
    try:
        if project_id is not None:
            storage_client = storage.Client(project=project_id)
        else:
            storage_client = storage.Client()

        bucket_names = [bucket.name for bucket in storage_client.list_buckets()]
        if bucket_names:
            for bucket_name in bucket_names:
                print(bucket_name)
        else:
            print("No buckets found or an error occurred.")
        return bucket_names
    except GoogleCloudError as e:
        print(f"Google Cloud Error: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def buckets_from_parser(args):
    list_buckets(project_id=args.pid)


def list_tif(bucket_name, prefix, limit):
    """
    List Cloud Storage objects with a specified prefix

    Args:
        bucket_name (str): The name of the Cloud Storage bucket.
        prefix (str, optional): Prefix for filtering objects within the bucket.
        limit (int, optional): Maximum number of TIF files to return.

    Returns:
        list: List of dictionaries containing properties of matching .tif files.
    """
    storage_client = storage.Client()
    search_prefix = prefix if prefix else ""
    fetch_limit = int(limit) * 10 if limit is not None else None

    if fetch_limit is not None:
        blobs = storage_client.list_blobs(
            bucket_name, prefix=search_prefix, max_results=fetch_limit
        )
    else:
        blobs = storage_client.list_blobs(bucket_name, prefix=search_prefix)

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

            if limit is not None and len(tif_files) >= int(limit):
                break

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

        print(json.dumps(list(subfolders), indent=2))
    except Exception as error:
        logging.error(f"Failed to fetch subfolders with error: {error}")
        return []


def subfolders_from_parser(args):
    subfolders(bucket_name=args.bucket)


def validate_cog(bucket_name, blob_name, detailed=False):
    """
    Validate that a GCS file is a proper Cloud Optimized GeoTIFF.

    Args:
        bucket_name (str): The name of the Cloud Storage bucket.
        blob_name (str): The path to the file within the bucket.
        detailed (bool): Whether to print detailed information.

    Returns:
        dict: Validation results with COG properties and STAC metadata.
    """
    cog_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"

    validation_result = {
        "is_valid_cog": False,
        "url": cog_url,
        "errors": [],
        "warnings": [],
        "properties": {},
        "stac_metadata": {}
    }

    try:
        with rasterio.open(cog_url) as src:
            # Basic properties
            validation_result["properties"] = {
                "driver": src.driver,
                "width": src.width,
                "height": src.height,
                "count": src.count,
                "dtype": str(src.dtypes[0]),
                "crs": str(src.crs) if src.crs else None,
                "nodata": src.nodata,
                "compression": src.compression.name if src.compression else None,
            }

            # STAC-compatible metadata
            stac_metadata = {
                "gsd": None,
                "proj:epsg": None,
                "proj:shape": [src.height, src.width],
                "raster:bands": []
            }

            # Extract EPSG code
            if src.crs:
                try:
                    stac_metadata["proj:epsg"] = src.crs.to_epsg()
                except Exception:
                    pass

            # Calculate GSD (ground sample distance)
            if src.transform:
                try:
                    gsd_x = abs(src.transform[0])
                    gsd_y = abs(src.transform[4])
                    stac_metadata["gsd"] = (gsd_x + gsd_y) / 2
                except Exception:
                    pass

            # Raster band information for STAC
            for i in range(1, src.count + 1):
                band_info = {
                    "nodata": src.nodata,
                    "data_type": str(src.dtypes[i-1]),
                    "spatial_resolution": stac_metadata["gsd"]
                }

                try:
                    stats = src.statistics(i)
                    if stats:
                        band_info["statistics"] = {
                            "minimum": stats.min,
                            "maximum": stats.max,
                            "mean": stats.mean,
                            "stddev": stats.std
                        }
                except Exception:
                    pass

                stac_metadata["raster:bands"].append(band_info)

            validation_result["stac_metadata"] = stac_metadata

            # Check for tiling
            if src.profile.get('tiled'):
                validation_result["properties"]["tiled"] = True
                validation_result["properties"]["blockxsize"] = src.profile.get('blockxsize')
                validation_result["properties"]["blockysize"] = src.profile.get('blockysize')
            else:
                validation_result["errors"].append("File is not tiled (required for COG)")

            # Check for overviews
            overviews_list = []
            for band_idx in range(1, src.count + 1):
                band_overviews = src.overviews(band_idx)
                if band_overviews:
                    overviews_list.append({f"band_{band_idx}": band_overviews})
                else:
                    validation_result["warnings"].append(f"Band {band_idx} has no overviews")

            if overviews_list:
                validation_result["properties"]["overviews"] = overviews_list
            else:
                validation_result["errors"].append("No overviews found (recommended for COG)")

            # Validate COG
            try:
                if src.profile.get('tiled') and overviews_list:
                    validation_result["is_valid_cog"] = True
            except Exception as e:
                validation_result["warnings"].append(f"Could not verify IFD offset: {str(e)}")

            # Additional metadata
            if detailed:
                validation_result["properties"]["bounds"] = src.bounds
                validation_result["properties"]["transform"] = list(src.transform)[:6]
                validation_result["properties"]["metadata"] = src.meta

            # Test random access
            try:
                window = rasterio.windows.Window(
                    col_off=src.width // 2,
                    row_off=src.height // 2,
                    width=min(256, src.width // 4),
                    height=min(256, src.height // 4)
                )
                data = src.read(1, window=window)
                validation_result["properties"]["random_access_test"] = "PASSED"
            except Exception as e:
                validation_result["errors"].append(f"Random access test failed: {str(e)}")
                validation_result["properties"]["random_access_test"] = "FAILED"

    except RasterioIOError as e:
        validation_result["errors"].append(f"Cannot open file: {str(e)}")
        return validation_result
    except Exception as e:
        validation_result["errors"].append(f"Validation error: {str(e)}")
        return validation_result

    return validation_result


def validate_cog_single_threaded(bucket_name, blob_name):
    """
    Wrapper for thread-safe COG validation.
    Returns tuple of (blob_name, validation_result)
    """
    try:
        result = validate_cog(bucket_name, blob_name, detailed=False)
        return (blob_name, result)
    except Exception as e:
        return (blob_name, {
            "is_valid_cog": False,
            "url": f"https://storage.googleapis.com/{bucket_name}/{blob_name}",
            "errors": [f"Validation failed: {str(e)}"],
            "warnings": [],
            "properties": {},
            "stac_metadata": {}
        })


def validate_cog_batch(bucket_name, prefix, limit, output_file=None, max_workers=10):
    """
    Validate multiple COGs in a bucket/prefix with concurrent validation.

    Args:
        bucket_name (str): The name of the Cloud Storage bucket.
        prefix (str): Prefix for filtering objects within the bucket.
        limit (int): Maximum number of files to validate.
        output_file (str, optional): Path to save validation results as JSON.
        max_workers (int): Number of concurrent validation threads (default: 10)
    """
    logging.info(f"Fetching TIF files from gs://{bucket_name}/{prefix or ''}")
    tif_files = list_tif(bucket_name, prefix, limit)

    if not tif_files:
        logging.warning("No TIF files found")
        return

    logging.info(f"Found {len(tif_files)} TIF files. Starting validation with {max_workers} workers...")

    results = []
    valid_count = 0
    invalid_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(validate_cog_single_threaded, bucket_name, tif_file.get("name")): tif_file
            for tif_file in tif_files
        }

        with tqdm(total=len(tif_files), desc="Validating COGs", unit="file") as pbar:
            for future in as_completed(future_to_file):
                tif_file = future_to_file[future]
                blob_name, validation_result = future.result()

                if validation_result["is_valid_cog"]:
                    valid_count += 1
                else:
                    invalid_count += 1

                pbar.set_postfix({"Valid": valid_count, "Invalid": invalid_count})

                results.append({
                    "file": blob_name,
                    "is_valid_cog": validation_result["is_valid_cog"],
                    "errors": validation_result["errors"],
                    "warnings": validation_result["warnings"],
                    "properties": validation_result["properties"],
                    "stac_metadata": validation_result["stac_metadata"]
                })

                pbar.update(1)

    print("\n" + "="*60)
    print(f"VALIDATION SUMMARY")
    print("="*60)
    print(f"Total files: {len(tif_files)}")
    print(f"Valid COGs: {valid_count}")
    print(f"Invalid COGs: {invalid_count}")
    print("="*60)

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logging.info(f"Results saved to {output_file}")

    return results


def validate_from_parser(args):
    """Parser function for validate command."""
    if args.batch or (args.limit and not args.blob) or args.prefix:
        validate_cog_batch(
            bucket_name=args.bucket,
            prefix=args.prefix,
            limit=args.limit,
            output_file=args.output,
            max_workers=args.workers
        )
    elif args.blob:
        result = validate_cog(
            bucket_name=args.bucket,
            blob_name=args.blob,
            detailed=args.detailed
        )
        print(json.dumps(result, indent=2))
    else:
        print("Error: Please provide either --blob for single file validation or use --batch/--limit for batch validation")


def get_property(data_list, target_name):
    matching_dicts = []
    for item in data_list:
        if "name" in item and target_name.lower() in item["name"].lower():
            matching_dicts.append(item)
    return matching_dicts


def register_single_asset_manifest(bucket_name, prefix, collection_path, asset_id, session, project, band_names=None):
    """
    Register a single COG asset using the manifest API (v1alpha).

    Args:
        bucket_name (str): GCS bucket name
        prefix (str): Prefix/folder path
        collection_path (str): Target EE collection path
        asset_id (dict): Asset metadata dictionary
        session: Authenticated session
        project (str): GEE project ID
        band_names (list): Optional list of band names
    """
    asset_name = asset_id.get('name').split('/')[-1].split('.')[0]
    asset_id_img = f"{collection_path}/{asset_name}"
    created_date = asset_id.get("time_created")
    updated_date = asset_id.get("time_updated")

    # Build GCS URI
    if prefix is None:
        uri = f"gs://{bucket_name}/{asset_id.get('name')}"
    else:
        uri = f"gs://{bucket_name}/{prefix}/{asset_id.get('name')}"

    # Get COG validation info for band metadata
    try:
        validation_result = validate_cog(bucket_name, asset_id.get('name'), detailed=False)
        band_count = validation_result.get('properties', {}).get('count', 1)
        stac_metadata = validation_result.get('stac_metadata', {})
    except Exception:
        band_count = 1
        stac_metadata = {}

    # Build band definitions
    bands = []
    if band_names and len(band_names) == band_count:
        for idx, band_name in enumerate(band_names):
            bands.append({
                'id': band_name,
                'tilesetId': '0',
                'tilesetBandIndex': idx
            })
    else:
        # Default band naming
        for idx in range(band_count):
            bands.append({
                'id': f'b{idx+1}',
                'tilesetId': '0',
                'tilesetBandIndex': idx
            })

    # Build properties from STAC metadata
    properties = {
        'file_size_bytes': asset_id.get("file_size_bytes")
    }

    if stac_metadata:
        if stac_metadata.get('gsd'):
            properties['gsd'] = stac_metadata['gsd']
        if stac_metadata.get('proj:epsg'):
            properties['epsg'] = stac_metadata['proj:epsg']

    # Build manifest payload
    manifest = {
        'imageManifest': {
            'name': asset_id_img,
            'tilesets': [
                {
                    'id': '0',
                    'sources': [{'uris': [uri]}]
                }
            ],
            'bands': bands,
            'properties': properties,
            'startTime': created_date,
            'endTime': updated_date,
        }
    }

    try:
        # Check if asset already exists
        if ee.data.getInfo(asset_id_img) is not None:
            return f"Asset {asset_id_img} already exists: SKIPPING"

        # Register using manifest API
        url = f'https://earthengine.googleapis.com/v1alpha/projects/{project}/image:importExternal'
        response = session.post(url=url, data=json.dumps(manifest))

        if response.status_code == 200:
            return f"Registered {asset_id_img}"
        else:
            return f"Failed to register {asset_id_img}: {response.text}"

    except ee.ee_exception.EEException as error:
        return f"Failed to register {asset_id_img}: {error}"
    except (KeyboardInterrupt, SystemExit):
        sys.exit("Program escaped by User")


def register_single_asset_legacy(bucket_name, prefix, collection_path, cred, account, asset_id):
    """Legacy registration method using gcs_location."""
    if cred and account is not None:
        credentials = ee.ServiceAccountCredentials(account, cred)
        ee.Initialize(credentials)
    else:
        ee.Initialize()

    asset_id_img = f"{collection_path}/{asset_id.get('name').split('/')[-1].split('.')[0]}"
    created_date = asset_id.get("time_created")
    updated_date = asset_id.get("time_updated")
    file_size_bytes = asset_id.get("file_size_bytes")

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

    try:
        if ee.data.getInfo(asset_id_img) is not None:
            return f"Asset {asset_id_img} already exists: SKIPPING"
        else:
            try:
                register = ee.data.createAsset(cog_manifest, asset_id_img)
                if register.get("id") is not None:
                    return f"Registered {asset_id_img}"
            except Exception as error:
                return f"Failed to register {asset_id_img} with error {error}"
    except ee.ee_exception.EEException:
        return f"Failed to register {asset_id_img}"
    except (KeyboardInterrupt, SystemExit):
        sys.exit("Program escaped by User")


def register(bucket_name, prefix, collection_path, cred, account, limit, band_names=None, use_manifest=True):
    """
    Register COG assets to an Earth Engine collection.

    Args:
        bucket_name (str): GCS bucket name
        prefix (str): Prefix/folder path
        collection_path (str): Target EE collection path
        cred (str): Path to service account credentials
        account (str): Service account email
        limit (int): Maximum number of assets to register
        band_names (list): Optional list of band names for multi-band COGs
        use_manifest (bool): Use manifest API (default: True)
    """
    # Initialize EE
    if cred and account is not None:
        credentials = ee.ServiceAccountCredentials(account, cred)
        ee.Initialize(credentials)
        session = AuthorizedSession(credentials)
        project = account.split('@')[1].split('.')[0]
    else:
        ee.Initialize()
        session, project = get_authenticated_session()
        if not project:
            logging.error("Could not determine project ID")
            return

    try:
        if ee.data.getAsset(collection_path):
            print(f"Collection exists: {ee.data.getAsset(collection_path)['id']}")
    except Exception:
        print(f"Collection does not exist: Creating {collection_path}")
        try:
            ee.data.createAsset({"type": ee.data.ASSET_TYPE_IMAGE_COLL_CLOUD}, collection_path)
        except Exception:
            ee.data.createAsset({"type": ee.data.ASSET_TYPE_IMAGE_COLL}, collection_path)

    assets_list = ee.data.getList(params={"id": collection_path})
    gee_asset_list = [os.path.basename(asset["id"]) for asset in assets_list]

    logging.info("Fetching TIF files from GCS...")
    ptif = list_tif(bucket_name, prefix, limit)
    gcs_asset_list = [file.get("name").split("/")[-1].split(".tif")[0] for file in ptif]
    remaining_items = set(gcs_asset_list) - set(gee_asset_list)
    print(f"Items left to register: {len(remaining_items)}")

    if len(remaining_items) > 0:
        with ThreadPoolExecutor() as executor:
            futures = []
            for object_name in remaining_items:
                asset_id = get_property(ptif, object_name)[0]

                if use_manifest:
                    future = executor.submit(
                        register_single_asset_manifest,
                        bucket_name, prefix, collection_path, asset_id,
                        session, project, band_names
                    )
                else:
                    future = executor.submit(
                        register_single_asset_legacy,
                        bucket_name, prefix, collection_path, cred, account, asset_id
                    )
                futures.append(future)

            with tqdm(total=len(futures), desc="Registering assets", unit="asset") as pbar:
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        logging.info(result)
                    pbar.update(1)

    elif len(remaining_items) == 0:
        print("All images already exist in the collection")


def register_from_parser(args):
    band_names = None
    if args.bands:
        band_names = [b.strip() for b in args.bands.split(',')]

    register(
        bucket_name=args.bucket,
        prefix=args.prefix,
        collection_path=args.collection,
        limit=args.limit,
        cred=args.cred,
        account=args.account,
        band_names=band_names,
        use_manifest=not args.legacy
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

    parser_validate = subparsers.add_parser(
        "validate", help="Validate COG structure and properties"
    )
    required_named = parser_validate.add_argument_group("Required named arguments.")
    required_named.add_argument(
        "--bucket", help="Google Cloud Project bucket name", required=True
    )

    optional_named = parser_validate.add_argument_group("Optional named arguments")
    optional_named.add_argument(
        "--blob", help="Specific blob/file to validate (single file mode)", default=None
    )
    optional_named.add_argument(
        "--prefix", help="Subfolder prefix (batch mode)", default=None
    )
    optional_named.add_argument(
        "--limit", help="Max number of files to validate (batch mode)", default=None, type=int
    )
    optional_named.add_argument(
        "--batch", help="Enable batch validation mode", action="store_true"
    )
    optional_named.add_argument(
        "--detailed", help="Show detailed properties", action="store_true"
    )
    optional_named.add_argument(
        "--output", help="Output file for validation results (JSON)", default=None
    )
    optional_named.add_argument(
        "--workers", help="Number of concurrent validation workers (default: 10)", default=10, type=int
    )

    parser_validate.set_defaults(func=validate_from_parser)

    parser_register = subparsers.add_parser(
        "register", help="Register COGs to GEE collection"
    )
    required_named = parser_register.add_argument_group("Required named arguments.")
    required_named.add_argument(
        "--bucket", help="Google Cloud Project bucket name", required=True
    )
    required_named.add_argument(
        "--collection", help="GEE collection path", required=True
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
    optional_named.add_argument(
        "--bands",
        help="Comma-separated list of band names (e.g., 'red,green,blue')",
        default=None,
    )
    optional_named.add_argument(
        "--legacy",
        help="Use legacy registration method instead of manifest API",
        action="store_true"
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
