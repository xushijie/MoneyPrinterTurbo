from loguru import logger

from app.config import config
from app.controllers.manager.memory_manager import InMemoryTaskManager
from app.controllers.manager.redis_manager import RedisTaskManager
from app.controllers.manager.chana_redis_manager import ChanaRedisTaskManager
from app.chana_ai.chana_video_combination_manager import ChanaVideoCombinationManager

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
    redis_cache = RedisTaskManager(max_concurrent_tasks=_max_concurrent_tasks, redis_url=redis_url)
    task_manager = ChanaRedisTaskManager(max_concurrent_tasks=_max_concurrent_tasks, redis_url=redis_url)
    orchetrator_manager = ChanaVideoCombinationManager(max_concurrent_tasks=_max_concurrent_tasks, redis_url=redis_url)
else:
    logger.success(f"init InMemory Task Manager...")
    task_manager = InMemoryTaskManager(max_concurrent_tasks=_max_concurrent_tasks)

