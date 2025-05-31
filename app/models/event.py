from pydantic import BaseModel
from typing import Optional, List, Tuple
from enum import Enum
from time import time
import json
"""
The classes in this file should be consistent with that 
    orchestrator: app/event/combine_event.py 

"""

class TypeEnum(Enum):
    advertise = "advertise"
    education = "education"
    
class StyleEnum(Enum):
    cinimation = "cinimation"
    animation = "animation"

class VideoMeta(BaseModel): 
    style: Optional[StyleEnum] = None
    aspect: Optional[str] = "16:9"
    type: Optional[TypeEnum] = None
    voice_volume: Optional[float] = 0.5
    bgm_type: Optional[str] = "custom"
    bgm_volume: Optional[float] = 0.2



class VideoCombineStatus(Enum):
    PENDING = "QUEUING"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
 
 
class ClipInfo(BaseModel):
    clip_id: int
    video_source_path: Optional[str] = None
    audio_source_path: Optional[str] = None
    subtitle_source_path: Optional[str] = None
    clip_duration: Optional[int] = 6   
    

"""
    VideoClipCombineTask is the task that is used to combine the video clips.
    It is used to store the task information in the database.
    It is also used to store the task information in the redis.
    在 MoneyPrint里面，这个数据是从MQ 中获取的，并且只读。
"""    
class VideoClipCombineTask(BaseModel):
    id: int
    task_id: str
    project_id: int
    stage_id: int
    user_id: int
    title: Optional[str] = None
    videoMeta: Optional[VideoMeta] = None
    clips: Optional[List[ClipInfo]] = None
    subtitle: Optional[str] = None
    audio: Optional[str] = None
    background_music: Optional[str] = None
    submit_time: Optional[int] = None

    
"""
    VideoClipCombineCompleteEvent is the event that is used to 生成任务执行信息的。.
    MoneyPrint负责填充各个字段，并最终从 MQ中发送出去，供Orchestratrator使用。 
    
"""
class VideoClipCombineCompleteEvent(BaseModel):
    id: int
    task_id: str
    project_id: int
    stage_id: int
    user_id: int
    status: str
    message: Optional[List[dict]] = []
    url: Optional[str] = None
    # Metric:  submit_time ==> start_time  ==> donwload_complete_time ==> end_time
    measure_time: Optional[List[Tuple[str, int, int]]] = []
    submit_time: Optional[int] = None
    
    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "project_id": self.project_id,
            "stage_id": self.stage_id,
            "user_id": self.user_id,
            "status": self.status,
            "message": self.message,
            "url": self.url,
            "measure_time": self.measure_time,
            "submit_time": self.submit_time
        }
    
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)