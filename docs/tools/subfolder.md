# Recursive tool
The `recursive` function is a utility within the `cogee` tool that lists and retrieves the names of subfolders (also known as prefixes) within a specified Google Cloud Storage bucket. It provides an efficient way to discover and work with subfolders in a Cloud Storage bucket.It connects to the Google Cloud Storage service using the Google Cloud Storage client library for Python. It retrieves the list of blobs (objects) within the specified bucket, extracts the subfolder names from their paths, and returns a list of these subfolder names.

#### Parameters

- `bucket_name` (str): The name of the Google Cloud Storage bucket for which you want to list recursive.

#### Returns

- `list`: A list of subfolder names within the specified bucket.

![cogee_recursive_tool](https://github.com/samapriya/cogee/assets/6677629/ba69b7da-223e-4bdb-b8aa-e96328e8054f)

#### Error Handling

- If the function encounters an error while accessing the Google Cloud Storage service (e.g., authentication issues, permission errors), it logs an error message and returns an empty list.
