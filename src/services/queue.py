# src/services/queue.py
import os
import redis
from rq import Queue

redis_url = (
    os.environ.get("REDIS_URL")
    or os.environ.get("RATELIMIT_STORAGE_URI")
    or "redis://localhost:6379/0"
)

_pool = redis.ConnectionPool.from_url(redis_url, max_connections=10, decode_responses=False)
_redis = redis.Redis(connection_pool=_pool)
q = Queue("default", connection=_redis)

def enqueue(func, *args, **kwargs):
    return q.enqueue(func, *args, **kwargs)
