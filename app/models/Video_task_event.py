from typing import Optional
from pydantic import BaseModel

class VideoTaskCompleteEvent(BaseModel):
    task_id: str    
    user_id: int
    path_names: Optional[list[str]] = None
    screenshort: Optional[str] = None
    status: Optional[int] = None
    message: Optional[str] = None  # 错误信息
    progress: Optional[int] = 0

    # {"endTime": "2024-10-19T01:09:31Z",    # 任何一个字段可以为 None
    # "startQueuingTime": "
    # 2024-10-19T01:01:33Z", 
    # "startProcessingTime": 
    # "2024-10-19T01:01:34Z"}
    stage_times: Optional[dict[str, str]] = None

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "path_names": self.path_names,
            "screenshort": self.screenshort,
            "status": self.status,
            "message": self.message,
            "stage_times": self.stage_times,
            "progress": self.progress,
        }