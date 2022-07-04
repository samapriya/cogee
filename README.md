# cogee: COG EE flow

#### Prerequisites

You need to have the correct permissions to your bucket, your cloud project, and GEE setup for this to work. Also install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) for your OS. The assumption is also that you enable Earth Engine API for your Google Cloud Project

- Next setup earthengine credentials using

```
earthengine authenticate
```

- Next initialize your google cloud sdk using

```
gcloud init
```

- Finally create app auth credentials using

```
gcloud auth application-default login
```

#### Setup environment

I always recommend that you setup a virtual environment to avoid disrupting anything else. Here is a great [primer on python virtual environment](https://realpython.com/python-virtual-environments-a-primer/)

To install **cogee: COG EE flow simply use**

`pip install cogee`

or you can also try

```
git clone https://github.com/samapriya/cogee.git
cd cogee
python setup.py install
```

#### Overall tools configuration

The comprehensive tool in its current state only has three options. Depending on how you setup your GEE environment you may or many not need the init tool

```
usage: cogee.py [-h] {init,buckets,register} ...

Simple CLI for COG registration to GEE

positional arguments:
  {init,buckets,register}
    init                GEE project auth
    buckets             Lists all Google Cloud Project buckets
    register            Register COGs to GEE collection

optional arguments:
  -h, --help            show this help message and exit
```

### cogee buckets

This is a simple tool that lists all buckets under a configured project that is available to you. You can run it by simply using

```
cogee buckets
```

#### cogee register

This tool is preconfigured to parse to specific COG names and syntax. Therefore, this is not a general-purpose tool for all registrations but can be modified to fit your needs.

```
usage: cogee register [-h] --bucket BUCKET [--prefix PREFIX] --collection
                         COLLECTION

optional arguments:
  -h, --help            show this help message and exit

Required named arguments.:
  --bucket BUCKET       Google Cloud Project bucket name
  --collection COLLECTION
                        GEE collection path

Optional named arguments:
  --prefix PREFIX       path/to/subfolder/
```

Simply pass your bucket, your prefix, and your collection path. This tool can create the collection path for you if it does not exist in GEE unless the path is a nested path and the parent folder is missing

```
cogee register --bucket "random-bucket-name" --collection "projects/random/assets/collection_name" --prefix "path/to/subfolder/"
```

## Changelog

#### v0.0.3

- allows for registering google service account for GEE
- allows for providing service account credentials as JSON for authentication 
