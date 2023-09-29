# Initialization tool

The `cogee init` tool is a command-line utility within the Cogee CLI for initializing and authenticating with Google Earth Engine (GEE). It streamlines the process of setting up the required authentication and credentials to access and interact with GEE services and datasets.

**Note:** Before calling this function, ensure that the necessary Google Cloud Platform and Earth Engine libraries are imported to your Python environment. **You only have to run this once unless you are changing projects**

#### Key Features

- **Earth Engine Initialization:** Quickly initialize and authenticate with GEE, enabling access to GEE's extensive geospatial data and analysis capabilities.

- **OAuth 2.0 Scopes:** Specifies the necessary OAuth 2.0 authentication scopes required for GEE access, ensuring secure and authorized interactions.

- **Credentials Retrieval:** Retrieves the Google Cloud Platform credentials and project ID associated with the specified scopes for seamless GEE integration.

- **Project Customization:** Specify the Google Cloud Platform project name to associate GEE interactions with the desired project.

#### Usage

```shell
cogee init --project PROJECT_NAME
```

![cogee_init](https://github.com/samapriya/cogee/assets/6677629/41cc6d06-1489-4d38-96ae-e81ef8d72f56)

## Required Arguments

- `--project PROJECT_NAME`: The name of the Google Cloud Platform project that you want to associate with GEE. This project will be used for GEE interactions and access.

## Example Usage

```shell
cogee init --project my-google-project
```

This command initializes and authenticates with Google Earth Engine using the specified Google Cloud Platform project name "my-google-project," enabling access to GEE's geospatial data and analysis capabilities within the context of this project.
