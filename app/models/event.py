from pydantic import BaseModel
from typing import Optional, List
from enum import Enum
import time
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
    submit_time: int = round(time.time() * 1000)

    
class VideoClipCombineCompleteEvent(BaseModel):
    id: int
    task_id: str
    project_id: int
    stage_id: int
    user_id: int
    status: VideoCombineStatus
    message: Optional[str] = ""
    url: Optional[str] = None
    # Metric:  submit_time ==> start_time  ==> donwload_complete_time ==> end_time
    start_time: int
    download_complete_time: Optional[int] = None
    upload_complete_time: Optional[int] = None
    end_time: Optional[int] = None
    
    # 错误信息
    error: Optional[str] = None
    
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)