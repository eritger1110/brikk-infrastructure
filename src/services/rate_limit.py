# -*- coding: utf-8 -*-
"""
Redis-based sliding window rate limiter for Brikk API.

Implements per-organization or per-API-key rate limiting with:
- Sliding window algorithm for smooth rate limiting
- Burst capacity for handling traffic spikes
- Standard X-RateLimit-* headers
- Graceful degradation when Redis is unavailable
- Configurable scoping (org vs key)
"""

import os
import time
import redis
from typing import Tuple, Optional, Dict, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class RateLimitResult:
    """Result of a rate limit check."""

    def __init__(
            self,
            allowed: bool,
            limit: int,
            remaining: int,
            reset_time: int,
            retry_after: Optional[int] = None):
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset_time = reset_time
        self.retry_after = retry_after

    def to_headers(self) -> Dict[str, str]:
        """Convert to standard rate limit headers."""
        headers = {
            'X-RateLimit-Limit': str(self.limit),
            'X-RateLimit-Remaining': str(max(0, self.remaining)),
            'X-RateLimit-Reset': str(self.reset_time)
        }

        if self.retry_after is not None:
            headers['Retry-After'] = str(self.retry_after)

        return headers


class RateLimitService:
    """Redis-based sliding window rate limiter."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize rate limiter.

        Args:
            redis_client: Optional Redis client. If None, creates from environment.
        """
        self.redis_client = redis_client or self._create_redis_client()
        self.window_size = 60  # 1 minute sliding window

        # Load configuration from environment
        self.enabled = self._get_bool_env('BRIKK_RLIMIT_ENABLED', False)
        self.per_minute_limit = self._get_int_env('BRIKK_RLIMIT_PER_MIN', 60)
        self.burst_capacity = self._get_int_env('BRIKK_RLIMIT_BURST', 20)
        self.scope = self._get_env(
            'BRIKK_RLIMIT_SCOPE',
            'org')  # 'org' or 'key'

        # Validate configuration
        if self.scope not in ['org', 'key']:
            logger.warning(
                f"Invalid BRIKK_RLIMIT_SCOPE '{self.scope}', defaulting to 'org'")
            self.scope = 'org'

        # Total limit includes burst capacity
        self.total_limit = self.per_minute_limit + self.burst_capacity

    def _create_redis_client(self) -> redis.Redis:
        """Create Redis client from environment configuration."""
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

        try:
            client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # Test connection
            client.ping()
            logger.info(f"Connected to Redis for rate limiting: {redis_url}")
            return client

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Return a mock client that always allows requests
            return self._create_mock_redis_client()

    def _create_mock_redis_client(self):
        """Create a mock Redis client for graceful degradation."""
        class MockRedis:
            def pipeline(self):
                return MockPipeline()

            def ping(self):
                return True

        class MockPipeline:
            def zremrangebyscore(self, *args, **kwargs):
                return self

            def zadd(self, *args, **kwargs):
                return self

            def zcard(self, *args, **kwargs):
                return self

            def expire(self, *args, **kwargs):
                return self

            def execute(self):
                return [0, 1, 0, True]  # Mock results

        return MockRedis()

    @staticmethod
    def _get_env(key: str, default: str) -> str:
        """Get environment variable as string."""
        return os.environ.get(key, default)

    @staticmethod
    def _get_bool_env(key: str, default: bool) -> bool:
        """Get environment variable as boolean."""
        value = os.environ.get(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')

    @staticmethod
    def _get_int_env(key: str, default: int) -> int:
        """Get environment variable as integer."""
        try:
            return int(os.environ.get(key, str(default)))
        except ValueError:
            logger.warning(
                f"Invalid integer value for {key}, using default {default}")
            return default

    def is_enabled(self) -> bool:
        """Check if rate limiting is enabled."""
        return self.enabled

    def get_scope_key(
            self,
            organization_id: Optional[str],
            api_key_id: Optional[str]) -> str:
        """
        Generate scope key for rate limiting.

        Args:
            organization_id: Organization ID from auth context
            api_key_id: API key ID from auth context

        Returns:
            Scope key for Redis
        """
        if self.scope == 'org' and organization_id:
            return f"rlimit:org:{organization_id}"
        elif self.scope == 'key' and api_key_id:
            return f"rlimit:key:{api_key_id}"
        else:
            # Fallback to anonymous scope
            return "rlimit:anonymous"

    def check_rate_limit(self, scope_key: str) -> RateLimitResult:
        """
        Check rate limit for a scope using sliding window algorithm.

        Args:
            scope_key: Redis key for the scope (org or API key)

        Returns:
            RateLimitResult with limit status and headers
        """
        if not self.enabled:
            # Rate limiting disabled - allow all requests
            return RateLimitResult(
                allowed=True,
                limit=self.total_limit,
                remaining=self.total_limit,
                reset_time=int(time.time()) + self.window_size
            )

        try:
            return self._check_rate_limit_redis(scope_key)
        except Exception as e:
            logger.error(f"Rate limit check failed for {scope_key}: {e}")
            # Graceful degradation - allow request when Redis fails
            return RateLimitResult(
                allowed=True,
                limit=self.total_limit,
                remaining=self.total_limit,
                reset_time=int(time.time()) + self.window_size
            )

    def _check_rate_limit_redis(self, scope_key: str) -> RateLimitResult:
        """
        Perform rate limit check using Redis sliding window.

        Uses a sorted set where:
        - Members are request timestamps
        - Scores are also timestamps for range queries
        - Window slides by removing old entries
        """
        now = time.time()
        window_start = now - self.window_size

        # Use Redis pipeline for atomic operations
        pipe = self.redis_client.pipeline()

        # Remove expired entries (outside sliding window)
        pipe.zremrangebyscore(scope_key, 0, window_start)

        # Add current request
        pipe.zadd(scope_key, {str(now): now})

        # Count current requests in window
        pipe.zcard(scope_key)

        # Set expiration for cleanup (window size + buffer)
        pipe.expire(scope_key, self.window_size + 60)

        # Execute pipeline
        results = pipe.execute()
        current_count = results[2]  # Result from zcard

        # Calculate remaining requests
        remaining = max(0, self.total_limit - current_count)
        allowed = current_count <= self.total_limit

        # Calculate reset time (when window will have space)
        reset_time = int(now + self.window_size)

        # Calculate retry-after for 429 responses
        retry_after = None
        if not allowed:
            # Estimate when the oldest request will expire
            try:
                oldest_scores = self.redis_client.zrange(
                    scope_key, 0, 0, withscores=True)
                if oldest_scores:
                    oldest_time = oldest_scores[0][1]
                    retry_after = max(
                        1, int(
                            oldest_time + self.window_size - now))
            except Exception:
                retry_after = self.window_size

        return RateLimitResult(
            allowed=allowed,
            limit=self.total_limit,
            remaining=remaining,
            reset_time=reset_time,
            retry_after=retry_after
        )

    def get_current_usage(self, scope_key: str) -> Dict[str, Any]:
        """
        Get current usage statistics for a scope.

        Args:
            scope_key: Redis key for the scope

        Returns:
            Dict with usage statistics
        """
        if not self.enabled:
            return {
                'enabled': False,
                'current_count': 0,
                'limit': self.total_limit,
                'remaining': self.total_limit,
                'window_size': self.window_size
            }

        try:
            now = time.time()
            window_start = now - self.window_size

            # Clean up expired entries and count current
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(scope_key, 0, window_start)
            pipe.zcard(scope_key)
            results = pipe.execute()

            current_count = results[1]
            remaining = max(0, self.total_limit - current_count)

            return {
                'enabled': True,
                'current_count': current_count,
                'limit': self.total_limit,
                'remaining': remaining,
                'window_size': self.window_size,
                'scope': self.scope,
                'per_minute_limit': self.per_minute_limit,
                'burst_capacity': self.burst_capacity
            }

        except Exception as e:
            logger.error(f"Failed to get usage for {scope_key}: {e}")
            return {
                'enabled': True,
                'error': str(e),
                'current_count': 0,
                'limit': self.total_limit,
                'remaining': self.total_limit,
                'window_size': self.window_size
            }

    def reset_scope(self, scope_key: str) -> bool:
        """
        Reset rate limit for a scope (admin function).

        Args:
            scope_key: Redis key for the scope

        Returns:
            True if reset successful, False otherwise
        """
        try:
            self.redis_client.delete(scope_key)
            logger.info(f"Reset rate limit for scope: {scope_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset rate limit for {scope_key}: {e}")
            return False

    def get_configuration(self) -> Dict[str, Any]:
        """
        Get current rate limiter configuration.

        Returns:
            Dict with configuration details
        """
        return {
            'enabled': self.enabled,
            'per_minute_limit': self.per_minute_limit,
            'burst_capacity': self.burst_capacity,
            'total_limit': self.total_limit,
            'window_size': self.window_size,
            'scope': self.scope,
            'redis_connected': self._test_redis_connection()
        }

    def _test_redis_connection(self) -> bool:
        """Test Redis connection."""
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check for rate limiter.

        Returns:
            Dict with health status
        """
        redis_healthy = self._test_redis_connection()

        return {
            'service': 'rate_limiter',
            'enabled': self.enabled,
            'redis_connected': redis_healthy,
            'configuration': self.get_configuration(),
            'status': 'healthy' if (
                not self.enabled or redis_healthy) else 'degraded',
            'timestamp': datetime.now(
                timezone.utc).isoformat()}


# Global rate limiter instance
_rate_limiter = None


def get_rate_limiter() -> RateLimitService:
    """Get global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimitService()
    return _rate_limiter


def reset_rate_limiter():
    """Reset global rate limiter instance (for testing)."""
    global _rate_limiter
    _rate_limiter = None
