
import os
import time
from app.services.oss import bucket
from loguru import logger


class OssUploader:
    def __init__(self):
        pass

    async def upload_from_local(
        self,
        local_path: str,
        remote_dir: str,
    ) -> str:
        try:
            # Generate unique filename using timestamp
            file_name = os.path.basename(local_path)
            base_file_name = file_name.split(".")[0]
            suffix = file_name.split(".")[-1]
            
            # Construct remote path
            oss_path = f"{remote_dir}/{base_file_name}_{int(time.time())}.{suffix}"
            
            # Upload file to OSS
            bucket.put_object_from_file(
                oss_path,
                local_path
            )
            
            # Return the full URL
            logger.info(f"Successfully uploaded file to OSS: {oss_path}")
            return oss_path
            
        except Exception as e:
            logger.error(f"Failed to upload file to OSS: {str(e)}")
            return None