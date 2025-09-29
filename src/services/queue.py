# src/services/queue.py
import os
import redis
from rq import Queue

_redis = redis.from_url(os.environ.get("REDIS_URL") or os.environ.get("RATELIMIT_STORAGE_URI") or "redis://localhost:6379/0")
q = Queue("default", connection=_redis)

def enqueue(func, *args, **kwargs):
    return q.enqueue(func, *args, **kwargs)
