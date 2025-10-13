# -*- coding: utf-8 -*-
"""
Caching Service

Provides a caching layer to reduce database load and improve performance.
"""

import os
import json
from typing import Any, Optional

import redis
from src.services.structured_logging import get_logger

logger = get_logger("brikk.caching")


class CachingService:
    """Service for caching data in Redis"""

    def __init__(self):
        self.redis_client = self._get_redis_client()
        self.default_ttl = int(
            os.getenv(
                "CACHE_DEFAULT_TTL_SECONDS",
                "3600"))  # 1 hour

    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client for caching"""
        try:
            # Use a different DB for cache
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/1")
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            logger.info("Caching service connected to Redis")
            return client
        except Exception as e:
            logger.warning(f"Redis not available for caching: {e}")
            return None

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache"""
        if not self.redis_client:
            return None

        try:
            cached_value = self.redis_client.get(key)
            if cached_value:
                logger.debug(f"Cache HIT for key: {key}")
                return json.loads(cached_value)
            else:
                logger.debug(f"Cache MISS for key: {key}")
                return None
        except Exception as e:
            logger.error(f"Failed to get from cache for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache"""
        if not self.redis_client:
            return

        if ttl is None:
            ttl = self.default_ttl

        try:
            serialized_value = json.dumps(value)
            self.redis_client.setex(key, ttl, serialized_value)
            logger.debug(f"Cached value for key: {key} with TTL: {ttl}s")
        except Exception as e:
            logger.error(f"Failed to set cache for key {key}: {e}")

    def delete(self, key: str) -> None:
        """Delete a value from the cache"""
        if not self.redis_client:
            return

        try:
            self.redis_client.delete(key)
            logger.debug(f"Deleted cache for key: {key}")
        except Exception as e:
            logger.error(f"Failed to delete cache for key {key}: {e}")

    def invalidate_tags(self, tags: list[str]) -> None:
        """Invalidate cache entries based on tags (requires Redis search or custom indexing)"""
        # This is a simplified implementation. A real-world scenario would use more
        # advanced techniques like Redisearch or maintaining sets of keys for
        # each tag.
        if not self.redis_client:
            return

        for tag in tags:
            # Example: delete all keys matching a pattern
            for key in self.redis_client.scan_iter(f"cache:{tag}:*"):
                self.delete(key)
            logger.info(f"Invalidated cache for tag: {tag}")


# Global caching service instance
caching_service = CachingService()
