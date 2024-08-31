import time
import threading
from loguru import logger
from typing import Callable, Any, Dict

from app.controllers.manager.redis_manager import RedisTaskManager
from app.services import oss
from app.utils import utils
from app.config import config
from app.services import state as sm
from app.models import const

class ChanaRedisTaskManager(RedisTaskManager):
    def __init__(self, max_concurrent_tasks: int, redis_url: str):
        super().__init__(max_concurrent_tasks, redis_url)
        self.counter = AtomicCounter()
        self.pool_size = max_concurrent_tasks
        self.max_queue_size = 16
        # @TODO: Although MultiProcess is preferable in python world, due to the GIL in the threading.
        # We still use thread as the tasks are IO-intensive.
        # self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.pool_size)
        self.threads = []
        self.event = threading.Event()

        for i in range(self.pool_size):
            thread = threading.Thread(target=self.run, name=f"worker_{i}", daemon=True)
            thread.start()
            self.threads.append(thread)
        logger.success("__init__ Chana Redis Manager")

    def add_task(self, func: Callable, *args: Any, **kwargs: Any):
        if self.get_queue_length() < self.max_queue_size:
            logger.success(f"enqueue task: {func.__name__}, current_tasks: {self.current_tasks}")
            self.enqueue({"func": func, "args": args, "kwargs": kwargs})
            return True
        else:
            logger.warning("The task is too busy..")
            return False

    def run(self):
        flag = False
        logger.info(f"Start thread..{threading.current_thread().name}")
        while not self.event.is_set():
            try:
                task_info = self.dequeue()
                if task_info:
                    flag = True
                    self.counter.inc()
                    logger.info(f"Scedule to run the task:  {task_info['kwargs']['task_id']}")
                    kwargs = task_info['func'](*task_info['args'], **task_info['kwargs'])
                    user_id = task_info['user_id']
                    self.post_process(task_info['kwargs']['task_id'], user_id, kwargs)
                time.sleep(1)
            except Exception as e:
                logger.exception(f"Caught an exception: {task_info['kwargs']['task_id']}, {e}")
            finally:
                if flag:
                    flag = False
                    self.counter.dec()

        logger.info("Finish thread")

    def post_process(self, task_id, user_id, kargs):
        """
        POST process a video and push it to the S3.
        {
             "videos": final_video_paths,
             "combined_videos": combined_video_paths,
             "screenshot": screenshot_path,
             "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        """
        final_videos = kargs.get("videos", [])
        oss_paths = []
        for i, final_video in enumerate(final_videos):
            path = oss.push_data_to_oss(final_video, f"{task_id}_{i}.mp4", user_id, 'video')
            oss_paths.append(path)

        scrshot = kargs.get('screenshot')
        screenshot_path = oss.push_data_to_oss(scrshot, f"{task_id}_screenshot.png", user_id, 'video')

        tmp = {
            "oss_final": str(oss_paths),
            "screenshot_final": screenshot_path
        }
        sm.state.update_task(task_id, state=const.TASK_COMPLETE, progress=100, **tmp)

        # @TODO  The local storage purge for `combined_videos` is DEFERRED here
        cached_videos = kargs.get('cached_videos', [])
        if not config.debug:
            utils.remove(cached_videos, final_videos)
            logger.info(f"Complete remove local caches for {task_id}")


class AtomicCounter(object):
    """An atomic, thread-safe counter"""

    def __init__(self, initial=0):
        """Initialize a new atomic counter to given initial value"""
        self._value = initial
        self._lock = threading.Lock()

    def inc(self, num=1):
        """Atomically increment the counter by num and return the new value"""
        with self._lock:
            self._value += num
            return self._value

    def dec(self, num=1):
        """Atomically decrement the counter by num and return the new value"""
        with self._lock:
            self._value -= num
            return self._value

    @property
    def value(self):
        return self._value
