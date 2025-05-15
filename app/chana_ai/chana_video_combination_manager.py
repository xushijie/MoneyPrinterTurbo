

import json
import os
import threading

from typing import Optional, Tuple
from loguru import logger
import asyncio

import requests
from app.chana_ai.oss_uploader import OssUploader
from app.config import config
from app.controllers.manager.chana_redis_manager import AtomicCounter
from app.controllers.manager.redis_manager import RedisTaskManager
from app.models import const
from app.models.event import VideoClipCombineCompleteEvent, VideoClipCombineTask, ClipInfo

from app.services import state as sm
from app.utils import utils
from moviepy.video.io.VideoFileClip import VideoFileClip
from app.chana_ai.chana_video_process import Chana_AI_Video_Process
from app.models.schema import VideoParams

from app.chana_ai.steps.step import ProcessContext, Step


class ChanaVideoCombinationManager(RedisTaskManager):
    def __init__(self, max_concurrent_tasks: int, redis_url: str):
        super().__init__(max_concurrent_tasks, redis_url)
        self.steps = [InitStep(), DownloadMaterialsStep(), MaterialBuilderStep(), CombineStep(), PostProcessStep()]
        self.counter = AtomicCounter()
        self.monitor_thread = threading.Thread(target=self.__start__, daemon=True)
        self.monitor_thread.start()
        logger.info("TasResubmitTask thread started")

    async def __start__(self):
        logger.info("ChanaVideoCombinationManager started..")
        while True:
            task_json = self.redis_client.brpop(config.compile_clips_queue)
            if task_json:
                event = VideoClipCombineCompleteEvent(**json.loads(task_json[1].decode("utf-8")))
                logger.info(f"serialized: {event}")
                asyncio.run(self.process_task(event))
                
            await asyncio.sleep(1)
    
    async def process_task(self, event: VideoClipCombineCompleteEvent):
        context = ProcessContext()
        for step in self.steps:
            await step.process(context, event)

# 初始化 目录和基本变量的值。
class InitStep(Step):
    async def process(self, context: ProcessContext, event: VideoClipCombineTask):
        context.redis_key = f"chana_task:{event.project_id}:{event.stage_id}:{event.task_id}"
        context.task_id = f"{event.project_id}_{event.stage_id}_{event.task_id}"
        context.task_path = utils.task_dir(sub_dir = context.task_id)
        

    def measure_time(self, context: ProcessContext, time_cost: float):
        context.measure_time_list["init"] = time_cost

    def update_progress(self, context: ProcessContext):
        sm.state.update_task(task_id= context.redis_key, state=const.TASK_STATE_PROCESSING, progress=5)


class DownloadMaterialsStep(Step):
    async def process(self, context: ProcessContext, event: VideoClipCombineTask):
        for clip in event.clips:
            results = await asyncio.gather(
                self.__download_resource__(redis_key=context.redis_key, url=clip.video_source_path, saved_dir=context.task_path, resource_type="video"),
                self.__download_resource__(redis_key=context.redis_key, url=clip.audio_source_path, saved_dir=context.task_path, resource_type="audio"),
                self.__download_resource__(redis_key=context.redis_key, url=clip.subtitle_source_path, saved_dir=context.task_path, resource_type="subtitle"),
                )
            
            local_clip = ClipInfo(
                clip_id=clip.clip_id,
            )
            
            for result in results:
                if result[0] == "video":
                    local_clip.video_source_path = result[1]
                elif result[0] == "audio":
                    local_clip.audio_source_path = result[1]
                elif result[0] == "subtitle":
                    local_clip.subtitle_source_path = result[1]
                    
            context.clip_list.append(local_clip)

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
        
    
    def measure_time(self, context: ProcessContext, time_cost: float):
        context.measure_time_list["download_materials"] = time_cost

    def update_progress(self, context: ProcessContext):
        sm.state.update_task(task_id= context.redis_key, state=const.TASK_STATE_PROCESSING, progress= 50)
        
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
            f.write(requests.get(url, proxies=config.proxy, verify=False, timeout=(60, 240)).content)

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


class MaterialBuilderStep(Step):
    async def process(self, context: ProcessContext, event: VideoClipCombineTask):
        context.audio_file = event.audio 
        context.subtitle_path = event.subtitle
        
        if(context.audio_file and context.subtitle_path):
            return 
        builder = []
        if event.audio:
            builder.append(self.__build_audio__(event))
        if event.subtitle:
            builder.append(self.__build_subtitle__(event))
            
        results = await asyncio.gather(*builder)
        for result in results:
            if result[0] == "audio" and not context.audio_file:
                context.audio_file = result[1]
            elif result[0] == "subtitle" and not context.subtitle_path:
                context.subtitle_path = result[1]
        
    def measure_time(self, context: ProcessContext, time_cost: float):
        pass
    
    # 返回值  audio local_file_path
    async def __build_audio__(self, event: VideoClipCombineTask) -> Tuple[str, str]:
        #TODO
        pass
    
    # 返回值  subtitle local_file_path
    async def __build_subtitle__(self, event: VideoClipCombineTask) -> Tuple[str, str]:
        #TODO 
        pass
    
    def update_progress(self, context: ProcessContext):
        sm.state.update_task(task_id= context.redis_key, state=const.TASK_STATE_PROCESSING, progress= 65)

class CombineStep(Step):
    video_process = Chana_AI_Video_Process()
    async def process(self, context: ProcessContext, event: VideoClipCombineTask):
        
        download_videos = [clip.video_source_path for clip in context.clip_list]
        clip_duration = sum(clip.clip_duration for clip in context.clip_list)
        videoParams = VideoParams(video_aspect=event.videoMeta.aspect, video_concat_mode=event.videoMeta.style, max_clip_duration=clip_duration)
        path = self.video_process(task_id=context.task_id, path=context.task_path, download_videos= download_videos, 
                           audio_file=context.audio_file, subtitle_path=context.subtitle_path, max_clip_duration=clip_duration, params=videoParams)
        context.local_path = path
    
    def measure_time(self, context: ProcessContext, time_cost: float):
        context.measure_time_list["combine"] = time_cost

    def update_progress(self, context: ProcessContext):
        sm.state.update_task(task_id= context.redis_key, state=const.TASK_STATE_PROCESSING, progress=90)

class PostProcessStep(Step):
    def __init__(self):
        self.oss_uploader = OssUploader()
        
    async def process(self, context: ProcessContext, event: VideoClipCombineCompleteEvent):
        oss_path = await self.oss_uploader.upload_from_local(local_path=context.local_path, remote_dir=context.task_id)
        context.oss_path = oss_path
    
    def measure_time(self, context: ProcessContext, time_cost: float):
        context.measure_time_list["uploader"] = time_cost

    def update_progress(self, context: ProcessContext):
        sm.state.update_task(task_id= context.redis_key, state=const.TASK_STATE_PROCESSING, progress=100)