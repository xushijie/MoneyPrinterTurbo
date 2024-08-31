import os
from typing import List
from loguru import logger
from app.utils import utils

from app.models.schema import VideoAspect, VideoParams, VideoConcatMode, MaterialInfo
from app.services import video as video_service


class BaseVideo:
    def get_bgm_file(self, bgm_type: str = "random", bgm_file: str = ""):
        return video_service.get_bgm_file(bgm_type, bgm_file)

    def combine_videos(self,
                       combined_video_path: str,
                       video_paths: List[str],
                       audio_file: str,
                       video_aspect: VideoAspect = VideoAspect.portrait,
                       video_concat_mode: VideoConcatMode = VideoConcatMode.random,
                       max_clip_duration: int = 5,
                       threads: int = 2,
                       ) -> str:
        return video_service.combine_videos(combined_video_path, video_paths, audio_file, video_aspect,
                                    video_concat_mode, max_clip_duration, threads)

    def add_subtitle(self,
                     video_path: str,
                     audio_path: str,
                     subtitle_path: str,
                     output_file: str,
                     params: VideoParams):
        return video_service.add_subtitle(video_path, audio_path, subtitle_path, output_file, params)

    def preprocess_video(self, materials: List[MaterialInfo], clip_duration=4):
        return video_service.preprocess_video(materials, clip_duration)

    def generate_video(self, video_path: str,
                   audio_path: str,
                   subtitle_path: str,
                   output_file: str,
                   params: VideoParams,
                   ):
        return video_service.generate_video(video_path, audio_path, subtitle_path, output_file, params)                   

class ChanaVideo(BaseVideo):
    def __init__(self):
        self.prefix = "oss"
    def download_oss_image(self, oss_image_uri: str, target_directory: str) -> str:
        """
        Downloads an OSS image with an expired time and signature to a target directory.

        Args:
        - oss_image_uri (str): The URI of the OSS image, including the expired time and signature.
        - target_directory (str): The directory where the image will be downloaded.

        Returns:
        - str: The final path name to the downloaded image.
        """
        import requests
        from urllib.parse import urlparse

        # Parse the URI to extract the filename
        parsed_uri = urlparse(oss_image_uri)
        filename = os.path.basename(parsed_uri.path)

        # Construct the local path for the downloaded file
        local_path = os.path.join(target_directory, filename)

        # Download the file
        try:
            with requests.get(oss_image_uri) as response:
                response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX/5XX
                with open(local_path, 'wb') as file:
                    file.write(response.content)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {oss_image_uri}: {str(e)}")
            return ""

        logger.info(f"Downloaded {oss_image_uri} to {local_path}")
        return local_path

    # extract URLs that 
    def preprocess_video(self, materials: List[MaterialInfo], clip_duration=4, task_id: str = ""):
        local_materials = []
        task_dir = utils.task_dir(task_id)
        logger.info(f'task_dir= {task_dir}')
        for material in materials:
            if not material.url.lower().startswith("http"):
                materials.remove(material)
                if not os.path.exists(material.url):
                    shutil.copy(material.url, task_dir)  
                
                filename = os.path.basename(material.url)
                material.url = os.path.join(task_dir, filename)      
            else:
                try:
                    local_path = self.download_oss_image(material.url, task_dir)
                    material.url = local_path
                except Exception as e:
                    logger.error(f"Failed to download {material.url}: {str(e)}")

            local_materials.append(material)  

        logger.info(f"List of local materials: {local_materials}")
        
        processed_materials = super().preprocess_video(local_materials, clip_duration)
        return processed_materials
       
    def extract_screenshot(self, video_path: str, screenshot_time: float = 0, output_path: str = ""):
        """
        Extracts a screenshot from an MP4 video at a specified time.

        Args:
            video_path (str): The path to the MP4 video file.
            screenshot_time (float, optional): The time in seconds from the start of the video to extract the screenshot. Defaults to 0.
            output_path (str, optional): The path to save the screenshot. Defaults to an empty string, which means the screenshot will be saved in the same directory as the video with a default name.

        Returns:
            str: The path to the saved screenshot.
        """
        import subprocess
        import tempfile

        # Construct the output path if not provided
        if not output_path:
            output_path = os.path.splitext(video_path)[0] + f"_screenshot_{screenshot_time:.2f}.png"

        # Use ffmpeg to extract the screenshot
        command = f"ffmpeg -i {video_path} -ss {screenshot_time} -vframes 1 {output_path}"
        try:
            subprocess.run(command, check=True, shell=True)
            logger.info(f"Screenshot extracted and saved to {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract screenshot: {e}")
            return ""


video = ChanaVideo()
