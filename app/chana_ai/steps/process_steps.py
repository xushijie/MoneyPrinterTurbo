
import os
import asyncio
import requests
from loguru import logger
from typing import Optional, Tuple

from app.services import state as sm
from app.utils import utils
from app.chana_ai.oss_uploader import OssUploader
from app.config import config
from moviepy.video.io.VideoFileClip import VideoFileClip
from app.chana_ai.chana_video_process import Chana_AI_Video_Process
from app.models.schema import VideoParams, VideoConcatMode
from app.models.event import VideoClipCombineCompleteEvent, VideoClipCombineTask, ClipInfo
from app.models import const
from app.chana_ai.steps.step import Step, ProcessContext
from app.chana_ai.redis_tool import redis_tool
from app.services.oss import generateSignedURL
# 初始化 目录和基本变量的值。
class InitStep(Step):
    async def process(self, context: ProcessContext, event: VideoClipCombineTask):
        context.redis_key = f"chana_task:{event.project_id}:{event.stage_id}:{event.task_id}"
        context.task_id = f"{event.project_id}_{event.stage_id}_{event.task_id}"
        context.task_path = utils.task_dir(sub_dir = context.task_id)
        

    def measure_time(self, context: ProcessContext, start_time: float, end_time: float):
        context.measure_time_list["init"] =  start_time, end_time

    def update_progress(self, context: ProcessContext):
        sm.state.update_task(task_id= context.redis_key, state=const.TASK_STATE_PROCESSING, progress=5)


class DownloadMaterialsStep(Step):
    async def process(self, context: ProcessContext, event: VideoClipCombineTask):
        for clip in event.clips:
            results = await asyncio.gather(
                self.__download_resource__(redis_key=context.redis_key, url=self.generate_oss_url(clip.video_source_path), saved_dir=context.task_path, resource_type="video"),
                self.__download_resource__(redis_key=context.redis_key, url=self.generate_oss_url(clip.audio_source_path), saved_dir=context.task_path, resource_type="audio"),
                self.__download_resource__(redis_key=context.redis_key, url=self.generate_oss_url(clip.subtitle_source_path), saved_dir=context.task_path, resource_type="subtitle"),
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
            if not local_clip.video_source_path:
                # TODO:  Skip this clip.
                logger.error(f"failed to download video: {clip.video_source_path}")
                return 
            
            context.clip_list.append(local_clip)

    def measure_time(self, context: ProcessContext, start_time: float, end_time: float):
        context.measure_time_list["download_materials"] = start_time, end_time

    def update_progress(self, context: ProcessContext):
        sm.state.update_task(task_id= context.redis_key, state=const.TASK_STATE_PROCESSING, progress= 50)

class MaterialBuilderStep(Step):
    async def process(self, context: ProcessContext, event: VideoClipCombineTask):
        PROJECT_AUDIO = "project_audio"
        PROJECT_BG_MUSIC = "project_bg_music"
        PROJECT_SUBTITLE = "project_subtitle"

        results = await asyncio.gather(
                self.__download_resource__(redis_key=context.redis_key, url=self.generate_oss_url(event.audio), saved_dir=context.task_path, resource_type=PROJECT_AUDIO),
                self.__download_resource__(redis_key=context.redis_key, url=self.generate_oss_url(event.background_music), saved_dir=context.task_path, resource_type=PROJECT_BG_MUSIC),
                self.__download_resource__(redis_key=context.redis_key, url=self.generate_oss_url(event.subtitle), saved_dir=context.task_path, resource_type=PROJECT_SUBTITLE),
                )
        
        for result in results:
            if result[0] == PROJECT_AUDIO:
                context.audio_file = result[1]
            elif result[0] == PROJECT_BG_MUSIC:
                context.bg_music_file = result[1]
            elif result[0] == PROJECT_SUBTITLE:
                context.subtitle_file = result[1]
            else: 
                logger.error(f"failed to download {result[0]}: {result[1]}")
            
        
    def measure_time(self, context: ProcessContext, start_time: float, end_time: float):
        context.measure_time_list["build_materials"] = start_time, end_time
    
    def update_progress(self, context: ProcessContext):
        sm.state.update_task(task_id= context.redis_key, state=const.TASK_STATE_PROCESSING, progress= 65)

class CombineStep(Step):
    video_process = Chana_AI_Video_Process()
    async def process(self, context: ProcessContext, event: VideoClipCombineTask):
        download_videos = [clip.video_source_path for clip in context.clip_list]
        clip_duration = sum(clip.clip_duration for clip in context.clip_list)
        #TODO:  Need to setup default value for videoParams.
        # BGM_FILE&BGM_TYPE&BGM_VOLUME in the videoParams. 当前并没有使用，和原来的moneyPrint兼容。
        videoParams = VideoParams(video_aspect=event.videoMeta.aspect,  
                                  video_subject=event.title,
                                  max_clip_duration=clip_duration, video_concat_mode= VideoConcatMode.sequential.value,
                                  subtitle_enabled=False, voice_name=context.audio_file, voice_volume=event.videoMeta.voice_volume,
                                  bgm_type=event.videoMeta.bgm_type, bgm_volume=event.videoMeta.bgm_volume, bgm_file= context.bg_music_file)
        path = await self.video_process(task_id=context.task_id, path=context.task_path, download_videos= download_videos, 
                           audio_file=context.audio_file, subtitle_path=context.subtitle_file, 
                           max_clip_duration=clip_duration, params=videoParams)
        context.local_path = path
    
    def measure_time(self, context: ProcessContext, start_time: float, end_time: float):
        context.measure_time_list["combine"] = start_time, end_time

    def update_progress(self, context: ProcessContext):
        sm.state.update_task(task_id= context.redis_key, state=const.TASK_STATE_PROCESSING, progress=90)

class PostProcessStep(Step):
    def __init__(self):
        self.oss_uploader = OssUploader()
        
    async def process(self, context: ProcessContext, event: VideoClipCombineCompleteEvent):
        oss_path = await self.oss_uploader.upload_from_local(local_path=context.local_path, remote_dir=context.task_id)
        context.oss_path = oss_path
    
    def measure_time(self, context: ProcessContext, start_time: float, end_time: float):
        context.measure_time_list["uploader"] = start_time, end_time

    def update_progress(self, context: ProcessContext):
        sm.state.update_task(task_id= context.redis_key, state=const.TASK_STATE_PROCESSING, progress=100)