import oss2
from loguru import logger
from app.config import config

# Replace with your own credentials and bucket information
ACCESS_KEY_ID = config.oss.get('id', '')
ACCESS_KEY_SECRET = config.oss.get('secret', '')
ENDPOINT = config.oss.get('end_point', 'https://oss-cn-beijing.aliyuncs.com')
BUCKET_NAME = config.oss.get('bucket', 'chana-video')

DIR_MAPPING = {
    "video": "generated",
    "material_music": "materials/music",
    "material_video": "materials/video",
    "material_image": "materials/image"
}

# Initialize the OSS Auth and Bucket objects
auth = oss2.Auth(ACCESS_KEY_ID, ACCESS_KEY_SECRET)
bucket = oss2.Bucket(auth, ENDPOINT, BUCKET_NAME)

def push_data_to_oss(file_path, object_name, userId, type="video"):
    """
    Uploads a file to Alibaba Cloud OSS.

    :param file_path: The local path to the file to be uploaded.
    :param object_name: The name of the object in OSS.
    """

    try:
        # The storage dir: 'generated/{userId}/{task_id}.mp4'
        dir = DIR_MAPPING.get(type, None)+"/"+str(userId)
        if not existDir(dir):
            bucket.put_object(dir+'/', b'')

        object_name = f'{dir}/{object_name}'
        # Upload the file
        result = bucket.put_object_from_file(object_name, file_path)
        # Check if the upload is successful
        if result.status == 200:
            logger.success(f"File {file_path} uploaded successfully to OSS as {object_name}")
            return object_name
        else:
            logger.success(f"Failed to upload file {file_path} to OSS. Status: {result.status}, Error: {result.resp.text}")
    except Exception as e:
        logger.exception(f"Error uploading file to OSS: {e}")

# def download_data_from_oss(object_name, download_path):
#     """
#     Downloads a file from Alibaba Cloud OSS.

#     :param object_name: The name of the object in OSS.
#     :param download_path: The local path where the file will be downloaded.
#     """
#     try:
#         object_name = get_target(object_name, type)
#         # Download the file
#         result = bucket.get_object_to_file(object_name, download_path)
#         # Check if the download is successful
#         if result.status == 200:
#             logger.success(f"File {download_path} downloaded successfully from OSS as {object_name}")
#         else:
#             logger.success(f"Failed to download file from OSS. Status: {result.status}, Error: {result.resp.text}")
#     except Exception as e:
#         logger.exception(f"Error downloading file from OSS: {e}")

def delete_resource(object_name: str, user_id: str, type: str):
    try:
        # The storage dir: 'generated/{userId}/{task_id}.mp4'
        dir = DIR_MAPPING.get(type, None)+"/"+user_id+"/"
        if not existDir(dir):
            return

        #@TODO 此处有潜在的bug, 因为可能多个视频。最后是删除这个 task_id,的前缀视频
        object_name = f'{dir}{object_name}_0.mp4'
        result = bucket.delete_object(object_name)
        if result.status == 204:
            print(f'Successfully removed {target} from OSS.')
        else:
            print(f'Failed to remove {target} from OSS. Status: {result.status}')
    except oss2.exceptions.OssError as e:
        print(f'Error occurred: {e}')

def existDir(directory_path):
    if not directory_path.endswith('/'):
        directory_path += '/'

    # List objects with the specified prefix
    object_iterator = oss2.ObjectIterator(bucket, prefix=directory_path)

    # Check if there is any object with the given prefix
    for obj in object_iterator:
        if obj.key.startswith(directory_path):
            return True

    return False


# Example usage
if __name__ == "__main__":
    local_file_path = '/work/python/MoneyPrinterTurbo/storage/tasks/010fea67-e39b-4044-8df3-6ffe9a460bb7/final-1.mp4'  # Replace with the path to your local file
    oss_object_name = '010fea67-e39b-4044-8df3-6ffe9a460bb7.mp4'    # Replace with the desired name in OSS

    push_data_to_oss(local_file_path, oss_object_name, 2, "video")
