

import json
import threading
import asyncio
from time import time
from loguru import logger
from app.config import config
from app.controllers.manager.chana_redis_manager import AtomicCounter
from app.controllers.manager.redis_manager import RedisTaskManager
from app.models.event import VideoClipCombineCompleteEvent, VideoClipCombineTask, CustomJSONEncoder
from app.chana_ai.steps.process_steps import InitStep, DownloadMaterialsStep, ProjectMaterialStep, CombineStep, PostProcessStep

from app.models.event import VideoCombineStatus
from app.chana_ai.steps.step import ProcessContext, Step


class ChanaVideoCombinationManager(RedisTaskManager):
    def __init__(self, max_concurrent_tasks: int, redis_url: str):
        super().__init__(max_concurrent_tasks, redis_url)
        self.steps = [InitStep(), DownloadMaterialsStep(), ProjectMaterialStep(), CombineStep(), PostProcessStep()]
        self.counter = AtomicCounter()
        self.monitor_thread = threading.Thread(target=self.__start__, daemon=True)
        self.monitor_thread.start()
        logger.info("TasResubmitTask thread started")

    def __start__(self):
        logger.info("ChanaVideoCombinationManager started..")
        while True:
            task = self.redis_client.brpop(config.compile_clips_queue)
            if task:
                task_json = task[1].decode("utf-8")
                logger.info(f"receive a clip task: {task_json}")
                event = VideoClipCombineTask(**json.loads(task_json))
                try:
                    asyncio.run(self.process_event(event))
                except Exception as e:
                    logger.error(f"error processing task: str{e}")
                    failed_event = VideoClipCombineCompleteEvent(
                        id=event.id,
                        task_id=event.task_id,
                        project_id=event.project_id,
                        stage_id=event.stage_id,
                        user_id=event.user_id,
                        status=VideoCombineStatus.FAILED.value,
                        # TODO:  better to construct a message with all the steps here. 目前只是临时方案
                        message=[{"step": "process_task", "message": str(e)}],
                        submit_time=int(time())
                    )
                    self.redis_client.lpush(config.compile_clips_complete_queue, json.dumps(failed_event.to_dict()))
                    continue
                
    
    async def process_event(self, event: VideoClipCombineTask):
        context = ProcessContext()
        for step in self.steps:
            await step(context, event)
            
        # Fire event
        complete_event = self.build_complete_event(context, event).to_dict()
        logger.info(f"complete_event: {complete_event}")
        self.redis_client.lpush(config.compile_clips_complete_queue, json.dumps(complete_event))
        
    def build_complete_event(self, context: ProcessContext, event: VideoClipCombineTask) -> VideoClipCombineCompleteEvent:
        return VideoClipCombineCompleteEvent(
            id=event.id,
            task_id=event.task_id,
            project_id=event.project_id,
            stage_id=event.stage_id,
            user_id=event.user_id,
            status= VideoCombineStatus.COMPLETE.value if context.oss_path else VideoCombineStatus.FAILED.value,
            message= [step.to_dict() for step in context.progresses],  
            url=context.oss_path,
            measure_time=context.measure_time_list,
            submit_time= int(time())
        )
    

if __name__ == "__main__":

    from app.controllers.v1.video import orchetrator_manager
    manager = orchetrator_manager

    task = '{"id": 67, "task_id": "CHANA_3d4d801d-a728-4ab8-8c12-0b3f96477633", "project_id": 29, "stage_id": 24, "user_id": 1, "title": "\u6d4b\u8bd52", "videoMeta": {"style": "animation", "aspect": "9:16", "type": "advertise"}, "clips": [{"clip_id": 388, "video_source_path": "orchestrator/1/29_24/388/1.mp4", "audio_source_path": null, "subtitle_source_path": null, "clip_duration": 6}, {"clip_id": 389, "video_source_path": "orchestrator/1/29_24/389/2.mp4", "audio_source_path": "orchestrator/1/29_24/389/29_24_389_voice.mp3", "subtitle_source_path": "orchestrator/1/29_24/389/29_24_389_subtitle.srt", "clip_duration": 6}, {"clip_id": 390, "video_source_path": "orchestrator/1/29_390/video/20250310212906.mp4", "audio_source_path": null, "subtitle_source_path": null, "clip_duration": 6}, {"clip_id": 391, "video_source_path": "orchestrator/1/29_24/391/4.mp4", "audio_source_path": null, "subtitle_source_path": null, "clip_duration": 6}, {"clip_id": 392, "video_source_path": "orchestrator/1/29_24/392/3.mp4", "audio_source_path": null, "subtitle_source_path": null, "clip_duration": 6}], "subtitle": "orchestrator/1/29_24/29_24_0_subtitle_1748771103537.srt", "audio": "orchestrator/1/29_24/29_24_0_voice_1748771103467.mp3", "background_music": null, "submit_time": 1748938467554}'
    task_dict = json.loads(task)
    event = VideoClipCombineTask(**task_dict)
    asyncio.run(manager.process_event(event))
    logger.info(f"event: complete..")
    