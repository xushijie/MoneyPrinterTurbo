

import json
import threading
import asyncio
from loguru import logger
from app.config import config
from app.controllers.manager.chana_redis_manager import AtomicCounter
from app.controllers.manager.redis_manager import RedisTaskManager
from app.models.event import VideoClipCombineCompleteEvent, VideoClipCombineTask, CustomJSONEncoder
from app.chana_ai.steps.process_steps import InitStep, DownloadMaterialsStep, MaterialBuilderStep, CombineStep, PostProcessStep

from app.models.event import VideoCombineStatus
from app.chana_ai.steps.step import ProcessContext, Step


class ChanaVideoCombinationManager(RedisTaskManager):
    def __init__(self, max_concurrent_tasks: int, redis_url: str):
        super().__init__(max_concurrent_tasks, redis_url)
        self.steps = [InitStep(), DownloadMaterialsStep(), MaterialBuilderStep(), CombineStep(), PostProcessStep()]
        self.counter = AtomicCounter()
        # self.monitor_thread = threading.Thread(target=self.__start__, daemon=True)
        # self.monitor_thread.start()
        logger.info("TasResubmitTask thread started")

    def __start__(self):
        logger.info("ChanaVideoCombinationManager started..")
        while True:
            task = self.redis_client.brpop(config.compile_clips_queue)
            if task:
                try:
                    task_json = task[1].decode("utf-8")
                    logger.info(f"receive a clip task: {task_json}")
                    event = VideoClipCombineTask(**json.loads(task_json))
                    asyncio.run(self.process_task(event))
                except Exception as e:
                    logger.error(f"error processing task: {e}")
                    continue
                
    
    async def process_task(self, event: VideoClipCombineTask):
        context = ProcessContext()
        for step in self.steps:
            await step.process(context, event)
            
        # Fire event
        complete_event = self.build_complete_event(context, event)
        await self.redis_client.lpush(config.compile_clips_complete_queue, json.dumps(complete_event))
        
    def build_complete_event(self, context: ProcessContext, event: VideoClipCombineTask) -> VideoClipCombineCompleteEvent:
        return VideoClipCombineCompleteEvent(
            id=event.id,
            task_id=event.task_id,
            project_id=event.project_id,
            stage_id=event.stage_id,
            user_id=event.user_id,
            status= VideoCombineStatus.COMPLETE if context.oss_path else VideoCombineStatus.FAILED,
            message= context.message,
            url=context.oss_path,
            start_time=context.measure_time_list["init"][0],
            end_time=context.measure_time_list[-1][1],
        )
    

if __name__ == "__main__":
    manager = ChanaVideoCombinationManager(max_concurrent_tasks=10, redis_url="redis://localhost:6379")

    task = '{"id": 53, "task_id": "CHANA_25070b12-6a5f-49c0-96aa-00ee24ce4a64", "project_id": 29, "stage_id": 24, "user_id": 1, "title": "海底奇遇记", "videoMeta": {"style": "animation", "aspect": "1:1", "type": "advertise"}, "clips": [{"clip_id": 388, "video_source_path": "orchestrator/1/29_24/388/1.mp4", "audio_source_path": null, "subtitle_source_path": null, "clip_duration": 6}, {"clip_id": 389, "video_source_path": "orchestrator/1/29_24/389/2.mp4", "audio_source_path": "orchestrator/1/29_24/389/29_24_389_voice.mp3", "subtitle_source_path": "orchestrator/1/29_24/389/29_24_389_subtitle.srt", "clip_duration": 6}, {"clip_id": 390, "video_source_path": "orchestrator/1/29_24/390/3.mp4", "audio_source_path": null, "subtitle_source_path": null, "clip_duration": 6}, {"clip_id": 391, "video_source_path": "orchestrator/1/29_24/391/4.mp4", "audio_source_path": null, "subtitle_source_path": null, "clip_duration": 6}, {"clip_id": 392, "video_source_path": "orchestrator/1/29_24/392/3.mp4", "audio_source_path": null, "subtitle_source_path": null, "clip_duration": 6}], "subtitle": null, "audio": null, "background_music": null, "submit_time": 1748435900245}'
    task_dict = json.loads(task)
    event = VideoClipCombineTask(**task_dict)
    asyncio.run(manager.process_task(event))
    logger.info(f"event: complete..")
    