import json
from typing import Dict
from loguru import logger

import redis

from app.controllers.manager.redis_manager import RedisTaskManager
from app.models.schema import VideoParams
from app.services import task as tm


class ChanaRedisTaskManager(RedisTaskManager):
    def __init__(self, max_concurrent_tasks: int, redis_url: str):
        logger.success("__init__ Chana Redis Manager")
        self.counter = AtomicCounter()
        self.pool_size = 10
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=pool_size)
        self.shutdown_event = threading.Event()
        super().__init__(max_concurrent_tasks, redis_url)

    def add_task(self, func: Callable, *args: Any, **kwargs: Any) :
        if self.counter.value() < self.max_concurrent_tasks:
            lgger.success(f"enqueue task: {func.__name__}, current_tasks: {self.current_tasks}")
            self.enqueue({"func": func, "args": args, "kwargs": kwargs})
            return  True
        else:
            logger.warning("The task is too busy..")
            return False

    def run():
        while not self.shutdown_event.is_set():
            try:
                Task task_info = dequeue()
                if task_info:
                    self.counter.incr()
                    task_info.func(*tash_info.args, **task_info.kwargs())

                    sleep(1)
            finally:
                self.counter.dec()
                logger.exception(f"receive an exception", args, kwargs)


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
