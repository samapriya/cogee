# Bucket List Tool

The Bucket List tool is a command-line utility for listing and displaying the names of all Google Cloud Storage buckets associated with a specified Google Cloud project.

#### Key Features

- **Bucket Listing:** Quickly and easily list all buckets in a Google Cloud project.

- **Error Handling:** Robust error handling ensures that common issues, such as authentication errors or invalid project IDs, are properly handled and reported.

- **Customizable:** The tool accepts a Google Cloud project ID as an argument, making it versatile for use with various projects.

![cogee_bucket_list](https://github.com/samapriya/cogee/assets/6677629/304c9608-c4a0-48e4-a7c2-380baf925a54)

#### Usage

```
cogee buckets --pid "Google Project ID"
```

- `pid` (optional): The ID of the Google Cloud project containing the buckets.

#### Error Handling

- If the specified `PROJECT_ID` is invalid or the Google Cloud project does not exist, an error message will be displayed.

- If an error occurs while accessing Google Cloud Storage (e.g., authentication issues, permission errors), an error message will be displayed.
