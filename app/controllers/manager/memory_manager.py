from queue import Queue
from typing import Dict
from loguru import logger

from app.controllers.manager.base_manager import TaskManager


class InMemoryTaskManager(TaskManager):
    def __init__(self):
        logger.success("__init__ Inmemory Manager")
        super(self)

    def create_queue(self):
        return Queue()

    def enqueue(self, task: Dict):
        self.queue.put(task)

    def enqueue_task_complete_event(self, task_id: str):
        logger.error("You should not seen this message..")

    def dequeue(self):
        return self.queue.get()

    def is_queue_empty(self):
        return self.queue.empty()
