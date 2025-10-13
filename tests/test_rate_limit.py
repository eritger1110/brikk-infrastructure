# -*- coding: utf-8 -*-

import os
import time
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from src.services.rate_limit import RateLimitService, RateLimitResult, get_rate_limiter, reset_rate_limiter


class TestRateLimitService:
    """Test the RateLimitService class."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True

        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [
            0, 1, 5, True]  # [removed, added, count, expire]
        mock_redis.pipeline.return_value = mock_pipeline

        return mock_redis

    @pytest.fixture
    def rate_limiter(self, mock_redis):
        """Create rate limiter with mock Redis."""
        return RateLimitService(redis_client=mock_redis)

    def test_rate_limiter_initialization(self, rate_limiter):
        """Test rate limiter initialization with default config."""
        assert rate_limiter.window_size == 60
        assert rate_limiter.per_minute_limit == 60
        assert rate_limiter.burst_capacity == 20
        assert rate_limiter.total_limit == 80
        assert rate_limiter.scope == "org"
        assert rate_limiter.enabled is False  # Default

    def test_rate_limiter_environment_config(self, mock_redis):
        """Test rate limiter configuration from environment."""
        with patch.dict(os.environ, {
            "BRIKK_RLIMIT_ENABLED": "true",
            "BRIKK_RLIMIT_PER_MIN": "100",
            "BRIKK_RLIMIT_BURST": "50",
            "BRIKK_RLIMIT_SCOPE": "key"
        }):
            limiter = RateLimitService(redis_client=mock_redis)
            assert limiter.enabled is True
            assert limiter.per_minute_limit == 100
            assert limiter.burst_capacity == 50
            assert limiter.total_limit == 150
            assert limiter.scope == "key"

    def test_scope_key_generation_org(self, rate_limiter):
        """Test scope key generation for organization scoping."""
        rate_limiter.scope = "org"

        key = rate_limiter.get_scope_key("test-org-123", "test-key-456")
        assert key == "rlimit:org:test-org-123"

        # Test fallback when org_id is None
        key = rate_limiter.get_scope_key(None, "test-key-456")
        assert key == "rlimit:anonymous"

    def test_scope_key_generation_key(self, rate_limiter):
        """Test scope key generation for API key scoping."""
        rate_limiter.scope = "key"

        key = rate_limiter.get_scope_key("test-org-123", "test-key-456")
        assert key == "rlimit:key:test-key-456"

        # Test fallback when key_id is None
        key = rate_limiter.get_scope_key("test-org-123", None)
        assert key == "rlimit:anonymous"

    def test_rate_limit_disabled(self, rate_limiter):
        """Test rate limiting when disabled."""
        rate_limiter.enabled = False

        result = rate_limiter.check_rate_limit("test-scope")

        assert result.allowed is True
        assert result.limit == 80
        assert result.remaining == 80
        assert result.retry_after is None

    def test_rate_limit_allowed(self, rate_limiter, mock_redis):
        """Test rate limiting when request is allowed."""
        rate_limiter.enabled = True

        # Mock Redis pipeline to return count below limit
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [
            0, 1, 5, True]  # 5 requests in window
        mock_redis.pipeline.return_value = mock_pipeline

        result = rate_limiter.check_rate_limit("test-scope")

        assert result.allowed is True
        assert result.limit == 80
        assert result.remaining == 75  # 80 - 5
        assert result.retry_after is None

        # Verify Redis operations
        mock_pipeline.zremrangebyscore.assert_called_once()
        mock_pipeline.zadd.assert_called_once()
        mock_pipeline.zcard.assert_called_once()
        mock_pipeline.expire.assert_called_once()

    def test_rate_limit_exceeded(self, rate_limiter, mock_redis):
        """Test rate limiting when limit is exceeded."""
        rate_limiter.enabled = True

        # Mock Redis pipeline to return count above limit
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [
            0, 1, 85, True]  # 85 requests in window
        mock_redis.pipeline.return_value = mock_pipeline

        # Mock oldest request time for retry-after calculation
        mock_redis.zrange.return_value = [("1640995140.123", 1640995140.123)]

        with patch("time.time", return_value=1640995200.0):  # Current time
            result = rate_limiter.check_rate_limit("test-scope")

        assert result.allowed is False
        assert result.limit == 80
        assert result.remaining == 0
        assert result.retry_after is not None
        assert result.retry_after > 0

    def test_rate_limit_headers(self, rate_limiter):
        """Test rate limit result header generation."""
        result = RateLimitResult(
            allowed=True,
            limit=100,
            remaining=75,
            reset_time=1640995200,
            retry_after=None
        )

        headers = result.to_headers()

        assert headers["X-RateLimit-Limit"] == "100"
        assert headers["X-RateLimit-Remaining"] == "75"
        assert headers["X-RateLimit-Reset"] == "1640995200"
        assert "Retry-After" not in headers

    def test_rate_limit_headers_with_retry_after(self, rate_limiter):
        """Test rate limit headers with retry-after."""
        result = RateLimitResult(
            allowed=False,
            limit=100,
            remaining=0,
            reset_time=1640995200,
            retry_after=45
        )

        headers = result.to_headers()

        assert headers["X-RateLimit-Limit"] == "100"
        assert headers["X-RateLimit-Remaining"] == "0"
        assert headers["X-RateLimit-Reset"] == "1640995200"
        assert headers["Retry-After"] == "45"

    def test_redis_connection_failure(self, rate_limiter):
        """Test graceful degradation when Redis fails."""
        rate_limiter.enabled = True

        # Mock Redis to raise exception
        rate_limiter.redis_client.pipeline.side_effect = Exception(
            "Redis connection failed")

        result = rate_limiter.check_rate_limit("test-scope")

        # Should allow request despite Redis failure
        assert result.allowed is True
        assert result.limit == 80
        assert result.remaining == 80

    def test_get_current_usage(self, rate_limiter, mock_redis):
        """Test getting current usage statistics."""
        rate_limiter.enabled = True

        # Mock Redis pipeline for usage check
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [0, 25]  # 25 current requests
        mock_redis.pipeline.return_value = mock_pipeline

        usage = rate_limiter.get_current_usage("test-scope")

        assert usage["enabled"] is True
        assert usage["current_count"] == 25
        assert usage["limit"] == 80
        assert usage["remaining"] == 55
        assert usage["scope"] == "org"

    def test_reset_scope(self, rate_limiter, mock_redis):
        """Test resetting rate limit for a scope."""
        mock_redis.delete.return_value = 1

        result = rate_limiter.reset_scope("test-scope")

        assert result is True
        mock_redis.delete.assert_called_once_with("test-scope")

    def test_health_check(self, rate_limiter, mock_redis):
        """Test rate limiter health check."""
        rate_limiter.enabled = True
        mock_redis.ping.return_value = True

        health = rate_limiter.health_check()

        assert health["service"] == "rate_limiter"
        assert health["enabled"] is True
        assert health["redis_connected"] is True
        assert health["status"] == "healthy"
        assert "configuration" in health
        assert "timestamp" in health


class TestRateLimitIntegration:
    """Test rate limiting integration with coordination endpoint."""

    @pytest.fixture
    def valid_envelope(self):
        """Create valid envelope data."""
        return {
            "version": "1.0",
            "message_id": "01234567-89ab-cdef-0123-456789abcdef",
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "message",
            "sender": {"agent_id": "test-agent"},
            "recipient": {"agent_id": "target-agent"},
            "payload": {"test": "data"},
            "ttl_ms": 30000
        }

    @pytest.fixture(autouse=True)
    def reset_rate_limiter_instance(self):
        """Reset global rate limiter instance before each test."""
        reset_rate_limiter()
        yield
        reset_rate_limiter()

    def test_coordination_rate_limit_disabled(self, client, valid_envelope):
        """Test coordination endpoint with rate limiting disabled."""
        with patch.dict(os.environ, {
            "BRIKK_RLIMIT_ENABLED": "false",
            "BRIKK_FEATURE_PER_ORG_KEYS": "false",
            "BRIKK_IDEM_ENABLED": "false"
        }):
            response = client.post(
                "/api/v1/coordination",
                data=json.dumps(valid_envelope),
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 202

            # Rate limit headers should not be present when disabled
            assert "X-RateLimit-Limit" not in response.headers
            assert "X-RateLimit-Remaining" not in response.headers
            assert "X-RateLimit-Reset" not in response.headers

    @patch("src.services.rate_limit.RateLimitService._create_redis_client")
    def test_coordination_rate_limit_allowed(
            self, mock_redis_factory, client, valid_envelope):
        """Test coordination endpoint with rate limiting enabled and request allowed."""
        # Mock Redis client
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [
            0, 1, 5, True]  # 5 requests in window
        mock_redis.pipeline.return_value = mock_pipeline
        mock_redis_factory.return_value = mock_redis

        with patch.dict(os.environ, {
            "BRIKK_RLIMIT_ENABLED": "true",
            "BRIKK_RLIMIT_PER_MIN": "60",
            "BRIKK_RLIMIT_BURST": "20",
            "BRIKK_FEATURE_PER_ORG_KEYS": "false",
            "BRIKK_IDEM_ENABLED": "false"
        }):
            response = client.post(
                "/api/v1/coordination",
                data=json.dumps(valid_envelope),
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 202

            # Rate limit headers should be present
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers

            assert response.headers["X-RateLimit-Limit"] == "80"  # 60 + 20
            assert int(response.headers["X-RateLimit-Remaining"]) >= 0

    @patch("src.services.rate_limit.RateLimitService._create_redis_client")
    def test_coordination_rate_limit_exceeded(
            self, mock_redis_factory, client, valid_envelope):
        """Test coordination endpoint with rate limit exceeded."""
        # Mock Redis client to return count above limit
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [
            0, 1, 85, True]  # 85 requests (above 80 limit)
        mock_redis.pipeline.return_value = mock_pipeline
        mock_redis.zrange.return_value = [("1640995140.123", 1640995140.123)]
        mock_redis_factory.return_value = mock_redis

        with patch.dict(os.environ, {
            "BRIKK_RLIMIT_ENABLED": "true",
            "BRIKK_RLIMIT_PER_MIN": "60",
            "BRIKK_RLIMIT_BURST": "20",
            "BRIKK_FEATURE_PER_ORG_KEYS": "false",
            "BRIKK_IDEM_ENABLED": "false"
        }):
            response = client.post(
                "/api/v1/coordination",
                data=json.dumps(valid_envelope),
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 429

            data = response.get_json()
            assert data["code"] == "rate_limited"
            assert data["message"] == "Rate limit exceeded"
            assert "request_id" in data

            # Rate limit headers should be present on 429 response
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
            assert "Retry-After" in response.headers

            assert response.headers["X-RateLimit-Limit"] == "80"
            assert response.headers["X-RateLimit-Remaining"] == "0"

    @patch("src.services.rate_limit.RateLimitService._create_redis_client")
    def test_coordination_rate_limit_burst_behavior(
            self, mock_redis_factory, client, valid_envelope):
        """Test burst capacity behavior."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_factory.return_value = mock_redis

        with patch.dict(os.environ, {
            "BRIKK_RLIMIT_ENABLED": "true",
            "BRIKK_RLIMIT_PER_MIN": "10",  # Low base limit
            "BRIKK_RLIMIT_BURST": "5",     # Small burst
            "BRIKK_FEATURE_PER_ORG_KEYS": "false",
            "BRIKK_IDEM_ENABLED": "false"
        }):
            # Test requests within burst capacity (total limit = 15)
            for count in [5, 10, 14]:  # Within limit
                mock_pipeline = MagicMock()
                mock_pipeline.execute.return_value = [0, 1, count, True]
                mock_redis.pipeline.return_value = mock_pipeline

                response = client.post(
                    "/api/v1/coordination",
                    data=json.dumps(valid_envelope),
                    headers={"Content-Type": "application/json"}
                )

                assert response.status_code == 202
                assert response.headers["X-RateLimit-Limit"] == "15"

            # Test request exceeding burst capacity
            mock_pipeline = MagicMock()
            mock_pipeline.execute.return_value = [
                0, 1, 16, True]  # Above limit
            mock_redis.pipeline.return_value = mock_pipeline
            mock_redis.zrange.return_value = [
                ("1640995140.123", 1640995140.123)]

            response = client.post(
                "/api/v1/coordination",
                data=json.dumps(valid_envelope),
                headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 429

    @patch("src.services.rate_limit.RateLimitService._create_redis_client")
    def test_coordination_rate_limit_scope_switching(
            self, mock_redis_factory, client, valid_envelope):
        """Test rate limiting with different scoping configurations."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [0, 1, 5, True]
        mock_redis.pipeline.return_value = mock_pipeline
        mock_redis_factory.return_value = mock_redis

        # Test with org scoping
        with patch.dict(os.environ, {
            "BRIKK_RLIMIT_ENABLED": "true",
            "BRIKK_RLIMIT_SCOPE": "org",
            "BRIKK_FEATURE_PER_ORG_KEYS": "false",
            "BRIKK_IDEM_ENABLED": "false"
        }):
            with patch.object(RateLimitService, "get_scope_key") as mock_get_scope_key:
                mock_get_scope_key.return_value = "rlimit:org:test-org-123"

                client.post(
                    "/api/v1/coordination",
                    data=json.dumps(valid_envelope),
                    headers={"Content-Type": "application/json"}
                )

                mock_get_scope_key.assert_called_once()

        # Test with key scoping
        with patch.dict(os.environ, {
            "BRIKK_RLIMIT_ENABLED": "true",
            "BRIKK_RLIMIT_SCOPE": "key",
            "BRIKK_FEATURE_PER_ORG_KEYS": "false",
            "BRIKK_IDEM_ENABLED": "false"
        }):
            with patch.object(RateLimitService, "get_scope_key") as mock_get_scope_key:
                mock_get_scope_key.return_value = "rlimit:key:test-key-456"

                client.post(
                    "/api/v1/coordination",
                    data=json.dumps(valid_envelope),
                    headers={"Content-Type": "application/json"}
                )

                mock_get_scope_key.assert_called_once()

    @patch("src.services.rate_limit.RateLimitService._create_redis_client")
    def test_coordination_rate_limit_redis_failure(
            self, mock_redis_factory, client, valid_envelope):
        """Test graceful degradation when Redis fails."""
        # Mock Redis to raise an exception
        mock_redis_factory.side_effect = Exception("Redis connection failed")

        with patch.dict(os.environ, {
            "BRIKK_RLIMIT_ENABLED": "true",
            "BRIKK_FEATURE_PER_ORG_KEYS": "false",
            "BRIKK_IDEM_ENABLED": "false"
        }):
            response = client.post(
                "/api/v1/coordination",
                data=json.dumps(valid_envelope),
                headers={"Content-Type": "application/json"}
            )

            # Should allow request despite Redis failure
            assert response.status_code == 202
            assert "X-RateLimit-Limit" not in response.headers

    @patch("src.services.rate_limit.RateLimitService._create_redis_client")
    @patch("src.services.idempotency.IdempotencyService._create_redis_client")
    def test_coordination_rate_limit_with_idempotency(
            self, mock_idem_redis, mock_rl_redis, client, valid_envelope):
        """Test interaction between rate limiting and idempotency."""
        # Mock Redis for both services
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_rl_redis.return_value = mock_redis
        mock_idem_redis.return_value = mock_redis

        # Mock idempotency check to return no conflict
        mock_redis.get.return_value = None

        with patch.dict(os.environ, {
            "BRIKK_RLIMIT_ENABLED": "true",
            "BRIKK_IDEM_ENABLED": "true"
        }):
            # First request, should be allowed and cached
            mock_pipeline = MagicMock()
            mock_pipeline.execute.return_value = [0, 1, 10, True]
            mock_redis.pipeline.return_value = mock_pipeline

            response1 = client.post(
                "/api/v1/coordination",
                data=json.dumps(valid_envelope),
                headers={
                    "Content-Type": "application/json",
                    "Idempotency-Key": "test-idem-key-123"
                }
            )

            assert response1.status_code == 202
            assert response1.headers["X-RateLimit-Remaining"] != "0"

            # Second request (idempotent), should not trigger rate limit check
            cached_response = {
                "status_code": 202,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"status": "accepted"})
            }
            mock_redis.get.return_value = json.dumps(cached_response)

            response2 = client.post(
                "/api/v1/coordination",
                data=json.dumps(valid_envelope),
                headers={
                    "Content-Type": "application/json",
                    "Idempotency-Key": "test-idem-key-123"
                }
            )

            assert response2.status_code == 202
            # Rate limit headers should not be present on cached response
            assert "X-RateLimit-Limit" not in response2.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
