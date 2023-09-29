# COG Register Tool

The `register` tool is a tool within the Cogee CLI for registering assets from a Google Cloud Storage (GCS) bucket into a Google Earth Engine (GEE) collection. This tool streamlines the process of ingesting geospatial data assets into GEE for analysis and visualization.

#### Key Features

- **Asset Registration:** Easily register assets from a GCS bucket into a specified GEE collection, making them accessible for GEE operations.

- **Subfolder Support:** Optionally specify a subfolder within the GCS bucket to register assets from. This allows for organized asset management.

- **Asset Limit:** Set a maximum number of assets to register, useful for controlling the size of your GEE collection.

- **Service Account Integration:** Authenticate with GEE using a service account for secure asset registration.

#### Usage

```
cogee register --bucket BUCKET --collection COLLECTION [--prefix PREFIX] [--limit LIMIT] [--cred CRED] [--account ACCOUNT]
```

![cogee_register](https://github.com/flatgeobuf/flatgeobuf/assets/6677629/c56054c1-1907-4d7c-a638-6eb62cc8bdec)


#### Required Arguments

- `--bucket BUCKET`: Specify the name of the Google Cloud Project bucket containing the assets you want to register.

- `--collection COLLECTION`: Provide the path to the GEE collection where the assets will be registered.

#### Optional Arguments

- `--prefix PREFIX`: Optionally specify a subfolder within the GCS bucket to register assets from.

- `--limit LIMIT`: Set a limit on the maximum number of assets to register. Useful for controlling collection size.

- `--cred CRED`: Path to the Credentials JSON file for the service account to authenticate with GEE.

- `--account ACCOUNT`: Service account email address for authentication.

#### Example Usage

```shell
cogee register --bucket my-google-bucket --collection users/myuser/mycollection --prefix mysubfolder --limit 100 --cred path/to/credentials.json --account service-account@example.com
```

This command registers assets from the "mysubfolder" subfolder in the "my-google-bucket" GCS bucket into the "users/myuser/mycollection" GEE collection, limiting the registration to 100 assets and authenticating with the specified service account.
