# src/services/queue.py
import os
from functools import lru_cache
import redis
from rq import Queue

def _redis_url() -> str:
    url = os.environ.get("REDIS_URL") or os.environ.get("RQ_REDIS_URL")
    if not url:
        raise RuntimeError("REDIS_URL not set")
    return url

@lru_cache()
def _queue() -> Queue:
    conn = redis.from_url(_redis_url())
    return Queue("default", connection=conn)

def enqueue(func, *args, **kwargs):
    """
    Enqueue a job into RQ. Raises clearly if REDIS_URL is missing.
    """
    return _queue().enqueue(func, *args, **kwargs)
