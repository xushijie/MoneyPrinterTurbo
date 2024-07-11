import time
import threading
import concurrent.futures
from typing import Callable, Dict, Any
from loguru import logger

from app.controllers.manager.redis_manager import RedisTaskManager


class ChanaRedisTaskManager(RedisTaskManager):
    def __init__(self, max_concurrent_tasks: int, redis_url: str):
        super().__init__(max_concurrent_tasks, redis_url)
        self.counter = AtomicCounter()
        self.pool_size = max_concurrent_tasks
        self.max_queue_size = 16
        #@TODO: Although MultiProcess is preferable in python world, due to the GIL in the threading.
        # We still use thread as the tasks are IO-intensive.
        # self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.pool_size)
        self.threads = []
        self.event = threading.Event()

        for i in range(self.pool_size):
            thread = threading.Thread(target=self.run, name=f"worker_{i}", daemon=True)
            thread.start()
            self.threads.append(thread)
            # self.executor.submit(self.run)
            # time.sleep(1)
        logger.success("__init__ Chana Redis Manager")

    def add_task(self, func: Callable, *args: Any, **kwargs: Any) :
        if  self.get_queue_length() < self.max_queue_size:
            logger.success(f"enqueue task: {func.__name__}, current_tasks: {self.current_tasks}")
            self.enqueue({"func": func, "args": args, "kwargs": kwargs})
            return True
        else:
            logger.warning("The task is too busy..")
            return False

    def run(self):
        flag  = False
        logger.info(f"Start thread..{threading.current_thread().name}")
        while not self.event.is_set():
            try:
                task_info = self.dequeue()
                if task_info:
                    flag = True
                    self.counter.inc()
                    logger.info(f"Scedule to run the task:  {task_info['kwargs']['task_id']}")
                    task_info['func'](*task_info['args'], **task_info['kwargs'])
                time.sleep(1)
            except Exception as e:
                logger.exception(f"Caught an exception: {task_info['kwargs']['task_id']}, {e}")
            finally:
                if flag:
                    flag = False
                    self.counter.dec()


        logger.info("Finish thread")


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
