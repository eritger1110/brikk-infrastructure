# src/services/queue.py
from __future__ import annotations
import os
from typing import Any
import redis
from rq import Queue

# Single source of truth for Redis URL.
# Use your Render Redis "Internal Key-Value URL" here via env var.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# One global connection that everyone (web & worker) should use.
# decode_responses=False keeps RQ binary-safe for pickled jobs.
_redis = redis.from_url(REDIS_URL, decode_responses=False)

# Queue name MUST match your worker start command. We use "default".
queue = Queue("default", connection=_redis)

def enqueue(func: Any, *args, **kwargs):
    """Enqueue a job on the default queue."""
    return queue.enqueue(func, *args, **kwargs)
