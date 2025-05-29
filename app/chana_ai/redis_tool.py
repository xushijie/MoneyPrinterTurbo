
import redis
from app.services.state import _redis_host, _redis_port, _redis_password, _redis_db

class RedisTool:
    def __init__(self):
        # TODO:   和 orchstrator 共享 redis 连接 , 将来分开吧。 除了 download url mapping 之外。
        self.redis_client = redis.StrictRedis(host=_redis_host, port=_redis_port, db=_redis_db, password=_redis_password)

    def get_redis_client(self):
        return self.redis_client    
    
    def get_object(self, key: str):
        serialized = self.redis_client.get(key)
        if not serialized:
            return None
        # 反序列化--- 仅仅使用对 字符串，不是 json 对象
        return serialized.decode("utf-8")
    
    def set_object(self, key: str, value: str, expires: int = 108000):
        self.redis_client.set(key, value, ex=expires)
        
        
redis_tool = RedisTool()