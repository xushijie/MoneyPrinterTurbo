from pydantic import BaseModel
from typing import Optional, List
from enum import Enum
import time

class TypeEnum(Enum):
    advertise = 1
    education = 2
    
class StyleEnum(Enum):
    cinimation = 1
    animation = 2

class VideoMeta(BaseModel): 
    style: Optional[StyleEnum] = None
    aspect: Optional[str] = "16:9"
    type: Optional[TypeEnum] = None


class VideoCombineStatus(Enum):
    PENDING = "QUEUING"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"

class ClipInfo(BaseModel):
    clip_id: str
    video_source_path: str
    audio_source_path: Optional[str] = None
    subtitle_source_path: Optional[str] = None
    clip_duration: Optional[int] = 6
    
class VideoClipCombineTask(BaseModel):   
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