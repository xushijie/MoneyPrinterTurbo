from typing import Optional
from pydantic import BaseModel

class VideoTaskCompleteEvent(BaseModel):
    taskId: str    
    userId: int
    pathNames: Optional[list[str]] = None
    screenshot: Optional[str] = None
    status: Optional[int] = None
    message: Optional[str] = None 
    progress: Optional[int] = 0

    # {"endTime": "2024-10-19T01:09:31Z",    # 任何一个字段可以为 None
    # "startQueuingTime": "
    # 2024-10-19T01:01:33Z", 
    # "startProcessingTime": 
    # "2024-10-19T01:01:34Z"}
    stage_times: Optional[dict[str, str]] = None

    def to_dict(self):
        return {
            "taskId": self.taskId,
            "userId": self.userId,
            "pathNames": self.pathNames,
            "screenshot": self.screenshot,
            "status": self.status,
            "message": self.message,
            "stageTimes": self.stage_times,
            "progress": self.progress,
        }