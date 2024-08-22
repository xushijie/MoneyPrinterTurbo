import os
import glob
import pathlib
import shutil
from datetime import datetime

from fastapi import Request, Depends, Path, BackgroundTasks, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.params import File
from loguru import logger

from app.config import config
from app.controllers import base
from app.controllers.manager.memory_manager import InMemoryTaskManager
from app.controllers.manager.chana_redis_manager import ChanaRedisTaskManager
from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.models.schema import TaskVideoRequest, TaskQueryResponse, TaskResponse, TaskQueryRequest, \
    BgmUploadResponse, BgmRetrieveResponse, TaskDeletionResponse
from app.services import task as tm
from app.services import state as sm
from app.utils import utils
from app.services.oss import delete_resource
# 认证依赖项
# router = new_router(dependencies=[Depends(base.verify_token)])
router = new_router()

_enable_redis = config.app.get("enable_redis", False)
_redis_host = config.app.get("redis_host", "localhost")
_redis_port = config.app.get("redis_port", 6379)
_redis_db = config.app.get("redis_db", 0)
_redis_password = config.app.get("redis_password", None)
_max_concurrent_tasks = config.app.get("max_concurrent_tasks", 1)

redis_url = f"redis://:{_redis_password}@{_redis_host}:{_redis_port}/{_redis_db}"
# 根据配置选择合适的任务管理器
if _enable_redis:
    logger.success(f"init RedisTaskManger...")
#    task_manager = RedisTaskManager(max_concurrent_tasks=_max_concurrent_tasks, redis_url=redis_url)
    task_manager = ChanaRedisTaskManager(max_concurrent_tasks=_max_concurrent_tasks, redis_url=redis_url)
else:
    logger.success(f"init InMemory Task Manager...")
    task_manager = InMemoryTaskManager(max_concurrent_tasks=_max_concurrent_tasks)


@router.post("/videos", response_model=TaskResponse, summary="Generate a short video")
def create_video(background_tasks: BackgroundTasks, request: Request, body: TaskVideoRequest):
    task_id = utils.get_uuid()
    request_id = base.get_task_id(request)
    user_id = base.get_user_id(request)
    if not user_id:
        logger.error(f'user id can not be null')
        return utils.get_response(status=401, message="User id can not be empty.")
    try:
        task = {
            "task_id": task_id,
            "request_id": request_id,
            "params": body.dict(),
        }

        params = body.dict()
        params['user_id'] = user_id
        sm.state.update_task(task_id, start=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id= user_id
                             )
        # background_tasks.add_task(tm.start, task_id=task_id, params=body)
        result = task_manager.add_task(tm.start, task_id=task_id, params=params)
        if result:
            logger.success(f"video created: {utils.to_json(task)}")
            return utils.get_response(200, task)
        return utils.get_response(status=201, message="Too many tasks are pending, please retry later")
    except ValueError as e:
        raise HttpException(task_id=task_id, status_code=400, message=f"{request_id}: {str(e)}")


@router.get("/tasks/{task_id}", response_model=TaskQueryResponse, summary="Query task status")
def get_task(request: Request, task_id: str = Path(..., description="Task ID"),
             query: TaskQueryRequest = Depends()):
    endpoint = config.app.get("endpoint", "")
    if not endpoint:
        endpoint = str(request.base_url)
    endpoint = endpoint.rstrip("/")

    request_id = base.get_task_id(request)
    task = sm.state.get_task(task_id)
    if task:
        return utils.get_response(200, task)

    raise HttpException(task_id=task_id, status_code=404, message=f"{request_id}: task not found")


@router.delete("/tasks/{task_id}", response_model=TaskDeletionResponse, summary="Delete a generated short video task")
def delete_video(request: Request, task_id: str = Path(..., description="Task ID")):
    request_id = base.get_task_id(request)
    task = sm.state.get_task(task_id)
    user_id = base.get_user_id(request)
    if not user_id:
        logger.error(f'user id can not be null')
        return utils.get_response(status=401, message="User id can not be empty.")

    if task:
        # tasks_dir = utils.task_dir()
        # current_task_dir = os.path.join(tasks_dir, task_id)
        # if os.path.exists(current_task_dir):
        #     shutil.rmtree(current_task_dir)

        sm.state.delete_task(task_id)
        # Delete OSS content
        delete_resource(task_id, user_id, "video")
        logger.success(f"video deleted: {utils.to_json(task)}")
        return utils.get_response(200)

    raise HttpException(task_id=task_id, status_code=404, message=f"{request_id}: task not found")


@router.get("/musics", response_model=BgmRetrieveResponse, summary="Retrieve local BGM files")
def get_bgm_list(request: Request):
    suffix = "*.mp3"
    song_dir = utils.song_dir()
    files = glob.glob(os.path.join(song_dir, suffix))
    bgm_list = []
    for file in files:
        bgm_list.append({
            "name": os.path.basename(file),
            "size": os.path.getsize(file),
            "file": file,
        })
    response = {
        "files": bgm_list
    }
    return utils.get_response(200, response)


@router.post("/musics", response_model=BgmUploadResponse, summary="Upload the BGM file to the songs directory")
def upload_bgm_file(request: Request, file: UploadFile = File(...)):
    request_id = base.get_task_id(request)
    # check file ext
    if file.filename.endswith('mp3'):
        song_dir = utils.song_dir()
        save_path = os.path.join(song_dir, file.filename)
        # save file
        with open(save_path, "wb+") as buffer:
            # If the file already exists, it will be overwritten
            file.file.seek(0)
            buffer.write(file.file.read())
        response = {
            "file": save_path
        }
        return utils.get_response(200, response)

    raise HttpException('', status_code=400, message=f"{request_id}: Only *.mp3 files can be uploaded")


@router.get("/stream/{file_path:path}")
async def stream_video(request: Request, file_path: str):
    tasks_dir = utils.task_dir()
    video_path = os.path.join(tasks_dir, file_path)
    range_header = request.headers.get('Range')
    video_size = os.path.getsize(video_path)
    start, end = 0, video_size - 1

    length = video_size
    if range_header:
        range_ = range_header.split('bytes=')[1]
        start, end = [int(part) if part else None for part in range_.split('-')]
        if start is None:
            start = video_size - end
            end = video_size - 1
        if end is None:
            end = video_size - 1
        length = end - start + 1

    def file_iterator(file_path, offset=0, bytes_to_read=None):
        with open(file_path, 'rb') as f:
            f.seek(offset, os.SEEK_SET)
            remaining = bytes_to_read or video_size
            while remaining > 0:
                bytes_to_read = min(4096, remaining)
                data = f.read(bytes_to_read)
                if not data:
                    break
                remaining -= len(data)
                yield data

    response = StreamingResponse(file_iterator(video_path, start, length), media_type='video/mp4')
    response.headers['Content-Range'] = f'bytes {start}-{end}/{video_size}'
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Content-Length'] = str(length)
    response.status_code = 206  # Partial Content

    return response


@router.get("/download/{file_path:path}")
async def download_video(_: Request, file_path: str):
    """
    download video
    :param _: Request request
    :param file_path: video file path, eg: /cd1727ed-3473-42a2-a7da-4faafafec72b/final-1.mp4
    :return: video file
    """
    tasks_dir = utils.task_dir()
    video_path = os.path.join(tasks_dir, file_path)
    file_path = pathlib.Path(video_path)
    filename = file_path.stem
    extension = file_path.suffix
    headers = {
        "Content-Disposition": f"attachment; filename={filename}{extension}"
    }
    return FileResponse(path=video_path, headers=headers, filename=f"{filename}{extension}",
                        media_type=f'video/{extension[1:]}')
