

from typing import Optional, Tuple
from datetime import time
import os
import requests
from loguru import  logger
from app.utils import utils
from app.models import const
from app.models.event import VideoClipCombineTask
from app.services import state as sm
from app.services.oss import generateSignedURL
from app.chana_ai.redis_tool import redis_tool
from moviepy.editor import VideoFileClip


class ProcessContext:
    def __init__(self):
        self.clip_list = []   # {clip_id: {video_source_path, audio_source_path, subtitle_source_path}}
        self.task_id = None
        self.task_path = None
        self.local_path = None
        self.oss_path = None
        self.measure_time_list = {}
        self.progress = RedisProgress()
        self.audio_file = None
        self.bg_music_file = None
        self.subtitle_file = None
        
        self.redis_key = None
        
class RedisProgress:
    state=const.TASK_STATE_FAILED
    progress=0
    message=""
    
class Step:
    def __init__(self):
        pass

    async def __call__(self, context: ProcessContext, event: VideoClipCombineTask):
        start_time = time.time()  
        message = None
        try:
            await self.process(context, event)
        except Exception as e:
            logger.error(f"Step {self.__class__.__name__} failed: {e}")
            message = str(e)
            raise e
        finally:    
            end_time = time.time()
            if message:
                self.update_progress(context=context, progress=100, status=const.TASK_STATE_FAILED, message=message)
            else: 
                self.update_progress(context=context)
            self.measure_time(context, start_time, end_time)

    async def process(self, context: ProcessContext, event: VideoClipCombineTask):
        pass
    
    def measure_time(self, context: ProcessContext, start_time: float, end_time: float):
        pass
    
    def update_progress(self, context: ProcessContext, progress: Optional[float] = None, status: Optional[str] = None, message: Optional[str] = None):
        sm.state.update_task(task_id= context.redis_key, state=const.TASK_STATE_FAILED, progress=100, message=message)

    async def __download_resource__(self, redis_key: str, url: str, saved_dir: str, resource_type: str) -> Optional[Tuple[str, str]]:
        try:
            if not url:
                logger.info(f"failed to download {resource_type}: {url}")
                return resource_type, None
            
            logger.info(f"downloading {resource_type}: {url}")
            saved_path = await self.__download__(url=url, save_dir=saved_dir, resource_type=resource_type)
            sm.state.update_task(task_id= redis_key, state=const.TASK_STATE_PROCESSING, progress= 30)
            if saved_path:
                logger.info(f"saved path to: {saved_path}")
                return resource_type, saved_path
            else:
                logger.error(f"failed to download {resource_type}: {url}")
                return resource_type, None
        except Exception as e:
            logger.error(f"failed to download {resource_type}: {url} => {str(e)}")

    async def __download__(self, url: str, save_dir: str = "", resource_type: str = "video") -> str:
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        url_without_query = url.split("?")[0]
        url_hash = utils.md5(url_without_query)
        video_id = f"vid-{url_hash}"
        suffix  = "mp4" if resource_type == "video" else "mp3" if resource_type == "audio" else "srt"
        download_path = f"{save_dir}/{video_id}.{suffix}"

        # if video already exists, return the path
        if os.path.exists(download_path) and os.path.getsize(download_path) > 0:
            logger.info(f"video already exists: {download_path}")
            return download_path

    
        with open(download_path, "wb") as f:
            f.write(requests.get(url, verify=False, timeout=(60, 240)).content)

        if resource_type == "video" and os.path.exists(download_path) and os.path.getsize(download_path) > 0:
            try:
                # To verify the video is valid
                clip = VideoFileClip(download_path)
                duration = clip.duration
                fps = clip.fps
                clip.close()
                if duration > 0 and fps > 0:
                    return download_path
            except Exception as e:
                try:
                    os.remove(download_path)
                except Exception as e:
                    pass
                logger.warning(f"invalid video file: {download_path} => {str(e)}")
        return None
    
    def generate_oss_url(self, key: str):
        if not key:
            return None
        cached_one = redis_tool.get_object(key)
        if cached_one:
            return cached_one
        else:
            oss_url = generateSignedURL(oss_path=key, expires=108000)
            redis_tool.set_object(key=key, value=oss_url, expires=108000)
            return oss_url     