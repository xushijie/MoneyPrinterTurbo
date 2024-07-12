import oss2
from loguru import logger

# Replace with your own credentials and bucket information
ACCESS_KEY_ID = 'your-access-key-id'
ACCESS_KEY_SECRET = 'your-access-key-secret'
ENDPOINT = 'http://oss-cn-hangzhou.aliyuncs.com'  # Adjust endpoint based on your region
BUCKET_NAME = 'your-bucket-name'

def push_data_to_oss(file_path, object_name):
    """
    Uploads a file to Alibaba Cloud OSS.

    :param file_path: The local path to the file to be uploaded.
    :param object_name: The name of the object in OSS.
    """
    # Initialize the OSS Auth and Bucket objects
    auth = oss2.Auth(ACCESS_KEY_ID, ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, ENDPOINT, BUCKET_NAME)
    
    try:
        # Upload the file
        result = bucket.put_object_from_file(object_name, file_path)
        # Check if the upload is successful
        if result.status == 200:
            logger.success(f"File {file_path} uploaded successfully to OSS as {object_name}")
        else:
            logger.success(f"Failed to upload file {file_path} to OSS. Status: {result.status}, Error: {result.resp.text}")
    except Exception as e:
        logger.exception(f"Error uploading file to OSS: {e}")

def download_data_from_oss(object_name, download_path):
    """
    Downloads a file from Alibaba Cloud OSS.

    :param object_name: The name of the object in OSS.
    :param download_path: The local path where the file will be downloaded.
    """
    # Initialize the OSS Auth and Bucket objects
    auth = oss2.Auth(ACCESS_KEY_ID, ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, ENDPOINT, BUCKET_NAME)
    
    try:
        # Download the file
        result = bucket.get_object_to_file(object_name, download_path)
        # Check if the download is successful
        if result.status == 200:
            logger.success(f"File {download_path} downloaded successfully from OSS as {object_name}")
        else:
            logger.success(f"Failed to download file from OSS. Status: {result.status}, Error: {result.resp.text}")
    except Exception as e:
        logger.exception(f"Error downloading file from OSS: {e}")

        
# Example usage
if __name__ == "__main__":
    local_file_path = 'path/to/your/local/file.txt'  # Replace with the path to your local file
    oss_object_name = 'your-oss-object-name.txt'    # Replace with the desired name in OSS
    
    push_data_to_oss(local_file_path, oss_object_name)

