

from typing import Optional
from datetime import time
from loguru import  logger
from app.models import const
from app.models.event import VideoClipCombineTask
from app.services import state as sm


class ProcessContext:
    def __init__(self):
        self.clip_list = []   # {clip_id: {video_source_path, audio_source_path, subtitle_source_path}}
        self.task_id = None
        self.task_path = None
        self.local_path = None
        self.oss_path = None
        self.measure_time_list = {}
        self.progress = RedisProgress()
        
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
            self.measure_time(context, end_time - start_time)

    async def process(self, context: ProcessContext, event: VideoClipCombineTask):
        pass
    
    def measure_time(self, context: ProcessContext, time_cost: float):
        pass
    
    def update_progress(self, context: ProcessContext, progress: Optional[float] = None, status: Optional[str] = None, message: Optional[str] = None):
        sm.state.update_task(task_id= context.redis_key, state=const.TASK_STATE_FAILED, progress=100, message=message)
