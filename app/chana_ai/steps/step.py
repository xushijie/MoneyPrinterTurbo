

from typing import Optional, Tuple
from time import time
import os
import requests
from loguru import  logger
from pydantic import BaseModel
from app.utils import utils
from app.models import const
from app.models.event import VideoClipCombineTask
from app.services import state as sm
from app.services.oss import generateSignedURL
from app.chana_ai.redis_tool import redis_tool
from moviepy.editor import VideoFileClip
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

"""
TODO  
1. 整个context 在最后结束的时候需要保存下来。 
2. 执行过程中的所有信息，尤其是错误等信息，需要记录下来。
3. 
"""
class ProcessContext:
    def __init__(self):
        self.clip_list = []   # {clip_id: {video_source_path, audio_source_path, subtitle_source_path}}
        self.task_id = None
        self.task_path = None
        self.local_path = None
        self.oss_path = None    # 合并后的oss_path 视频路径，需要作为消息返回
        self.oss_remote_dir = None   # 合并后的oss_path 视频目录，在生成 oss_path的时候需要使用。
        self.measure_time_list = []
        self.progresses = []
        self.audio_file = None
        self.bg_music_file = None
        self.subtitle_file = None        
        self.redis_key = None
        
class Progress(BaseModel):
    label: str
    status: int
    progress: int
    message: Optional[str] = ""

    def to_dict(self):
        return {
            "label": self.label,
            "status": self.status,
            "progress": self.progress,
            "message": self.message
        }

class Step:
    step_name = None
    progress = 0
    
    def __init__(self):
        pass

    async def __call__(self, context: ProcessContext, event: VideoClipCombineTask):
        start_time = time()  
        message = None
        try:
            await self.process(context, event)
        except Exception as e:
            context.status = const.TASK_STATE_FAILED
            logger.error(f"Step {self.__class__.__name__} failed: {e}")
            message = str(e)
            raise e
        finally:    
            end_time = time()
            if message:
                self.update_progress(context=context, progress=100, status=const.TASK_STATE_FAILED, message=message)
            else: 
                self.update_progress(context=context, progress= self.progress, status = const.TASK_STATE_PROCESSING)
            self.measure_time(context, int(start_time), int(end_time))

    async def process(self, context: ProcessContext, event: VideoClipCombineTask):
        pass
    
    def measure_time(self, context: ProcessContext, start_time: float, end_time: float):
        context.measure_time_list.append((self.step_name, start_time, end_time))
    
    def update_progress(self, context: ProcessContext, progress: Optional[int], status: Optional[int], message: Optional[str] = ''):
        context.progresses.append(Progress(label=self.step_name, progress=progress, status=status, message=message))
        context.status = "SUCCESS" if progress == 100 else status
        sm.state.update_task(task_id= context.redis_key, state=status, progress=progress, message=message)

    async def __download_resource__(self, redis_key: str, url: str, saved_dir: str, resource_type: str) -> Optional[Tuple[str, str]]:
        try:
            if not url:
                logger.info(f"Skipping download {resource_type}: {url} due to empty url" )
                return resource_type, None
            
            oss_url = self.generate_oss_url(url)
            logger.info(f"downloading {resource_type}: {url} =》 {oss_url}")
            saved_path = await self.__download__(url=oss_url, save_dir=saved_dir, resource_type=resource_type)
            sm.state.update_task(task_id= redis_key, state=const.TASK_STATE_PROCESSING, progress= 30)
            if saved_path:
                logger.info(f"saved path to: {saved_path}")
                return resource_type, saved_path
            else:
                logger.error(f"failed to download {resource_type}: {url}  => {oss_url}")
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

        download_result = self.__download_with_retry__(url, download_path=download_path)
        
        if download_result and resource_type == "video" and os.path.exists(download_path) and os.path.getsize(download_path) > 0:
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
                    logger.error('exception during check donwload result {e} for {url}')
                    os.remove(download_path)
                except Exception as e:
                    pass
                logger.warning(f"invalid video file: {download_path} => {str(e)}")
            return None

        # Return donwload_path if it is non-video. (Audio, src cases)
        return download_path
    
    def generate_oss_url(self, key: str, use_cache: bool = False, expires: int = 75000):
        if not key:
            return None
        if use_cache: 
            cached_one = redis_tool.get_object(key)
            if cached_one:
                return cached_one
        
        oss_url = generateSignedURL(oss_path=key, expires=expires)
        redis_tool.set_object(key=key, value=oss_url, expires= int(expires*0.8)) # Less than 80% of the URL life time.
        return oss_url     

    def __download_with_retry__(self, url, download_path, max_retries=3, backoff_factor=1):
        session = requests.Session()
        
        # 配置重试策略
        retry = Retry(
            total=max_retries,                 # 总重试次数
            connect=max_retries,               # 连接错误重试次数
            read=max_retries,                  # 读取超时重试次数
            backoff_factor=backoff_factor,     # 退避因子（等待时间：1, 2, 4, 8...）
            status_forcelist=[500, 502, 503, 504],  # 对这些状态码进行重试
            allowed_methods=["GET"]            # 仅对GET请求重试（默认）
        )
        
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        try:
            response = session.get(url, verify=False, timeout=(60, 240))
            response.raise_for_status()  # 非2xx状态码抛出异常
            with open(download_path, "wb") as f:
                f.write(response.content)
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"下载失败: {e}")
            return False
        finally:
            session.close()