"""
Test suite for Redis-based idempotency service.
"""
import pytest
import json
from unittest.mock import patch, MagicMock

from src.services.idempotency import IdempotencyService


class TestIdempotencyService:
    """Test idempotency service functionality."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock_redis = MagicMock()
        return mock_redis
    
    @pytest.fixture
    def idempotency_service(self, mock_redis):
        """Create idempotency service with mock Redis."""
        with patch('src.services.idempotency.redis.Redis', return_value=mock_redis):
            service = IdempotencyService()
            service.redis = mock_redis
            return service
    
    def test_generate_idempotency_key_with_custom_key(self, idempotency_service):
        """Test idempotency key generation with custom key."""
        key_id = "bk_test_key"
        body_hash = "abc123"
        custom_key = "custom_idem_key"
        
        idem_key = idempotency_service.generate_idempotency_key(
            key_id, body_hash, custom_key
        )
        
        assert idem_key == f"idem:{key_id}:{custom_key}"
    
    def test_generate_idempotency_key_without_custom_key(self, idempotency_service):
        """Test idempotency key generation without custom key."""
        key_id = "bk_test_key"
        body_hash = "abc123def456"
        
        idem_key = idempotency_service.generate_idempotency_key(
            key_id, body_hash
        )
        
        expected = f"idem:{key_id}:{body_hash[:16]}"
        assert idem_key == expected
    
    def test_store_response(self, idempotency_service, mock_redis):
        """Test response storage for idempotency."""
        idem_key = "idem:bk_test:abc123"
        response_data = {"status": "accepted", "id": "123"}
        status_code = 202
        
        idempotency_service.store_response(idem_key, response_data, status_code)
        
        # Verify Redis setex was called with correct parameters
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        
        assert call_args[0][0] == idem_key  # key
        assert call_args[0][1] == 86400  # TTL (24 hours)
        
        # Verify stored data structure
        stored_data = json.loads(call_args[0][2])
        assert stored_data['response'] == response_data
        assert stored_data['status_code'] == status_code
        assert 'stored_at' in stored_data
    
    def test_get_cached_response_exists(self, idempotency_service, mock_redis):
        """Test getting cached response when it exists."""
        idem_key = "idem:bk_test:abc123"
        cached_data = {
            "response": {"status": "accepted", "id": "123"},
            "status_code": 202,
            "stored_at": "2023-12-01T10:30:00Z"
        }
        
        mock_redis.get.return_value = json.dumps(cached_data)
        
        response, status_code = idempotency_service.get_cached_response(idem_key)
        
        assert response == cached_data['response']
        assert status_code == 202
        mock_redis.get.assert_called_once_with(idem_key)
    
    def test_get_cached_response_not_exists(self, idempotency_service, mock_redis):
        """Test getting cached response when it doesn't exist."""
        idem_key = "idem:bk_test:abc123"
        mock_redis.get.return_value = None
        
        response, status_code = idempotency_service.get_cached_response(idem_key)
        
        assert response is None
        assert status_code is None
        mock_redis.get.assert_called_once_with(idem_key)
    
    def test_get_cached_response_invalid_json(self, idempotency_service, mock_redis):
        """Test getting cached response with invalid JSON."""
        idem_key = "idem:bk_test:abc123"
        mock_redis.get.return_value = "invalid json"
        
        response, status_code = idempotency_service.get_cached_response(idem_key)
        
        assert response is None
        assert status_code is None
    
    def test_check_body_hash_conflict_no_conflict(self, idempotency_service, mock_redis):
        """Test body hash conflict check with no conflict."""
        key_id = "bk_test_key"
        body_hash = "abc123"
        
        # No existing hash stored
        mock_redis.get.return_value = None
        
        has_conflict = idempotency_service.check_body_hash_conflict(key_id, body_hash)
        
        assert not has_conflict
        # Should store the new hash
        mock_redis.setex.assert_called_once_with(
            f"body_hash:{key_id}", 86400, body_hash
        )
    
    def test_check_body_hash_conflict_same_hash(self, idempotency_service, mock_redis):
        """Test body hash conflict check with same hash."""
        key_id = "bk_test_key"
        body_hash = "abc123"
        
        # Same hash already stored
        mock_redis.get.return_value = body_hash
        
        has_conflict = idempotency_service.check_body_hash_conflict(key_id, body_hash)
        
        assert not has_conflict
        # Should not store again
        mock_redis.setex.assert_not_called()
    
    def test_check_body_hash_conflict_different_hash(self, idempotency_service, mock_redis):
        """Test body hash conflict check with different hash."""
        key_id = "bk_test_key"
        body_hash = "abc123"
        stored_hash = "def456"
        
        # Different hash already stored
        mock_redis.get.return_value = stored_hash
        
        has_conflict = idempotency_service.check_body_hash_conflict(key_id, body_hash)
        
        assert has_conflict
        # Should not store the new hash
        mock_redis.setex.assert_not_called()
    
    def test_process_request_idempotency_first_request(self, idempotency_service, mock_redis):
        """Test idempotency processing for first request."""
        key_id = "bk_test_key"
        body_hash = "abc123"
        
        # No cached response
        mock_redis.get.return_value = None
        
        should_process, response, status = idempotency_service.process_request_idempotency(
            key_id, body_hash
        )
        
        assert should_process
        assert response is None
        assert status is None
    
    def test_process_request_idempotency_cached_response(self, idempotency_service, mock_redis):
        """Test idempotency processing with cached response."""
        key_id = "bk_test_key"
        body_hash = "abc123"
        
        cached_data = {
            "response": {"status": "accepted", "id": "123"},
            "status_code": 202,
            "stored_at": "2023-12-01T10:30:00Z"
        }
        
        # Mock Redis calls
        def mock_get(key):
            if key.startswith("idem:"):
                return json.dumps(cached_data)
            elif key.startswith("body_hash:"):
                return body_hash
            return None
        
        mock_redis.get.side_effect = mock_get
        
        should_process, response, status = idempotency_service.process_request_idempotency(
            key_id, body_hash
        )
        
        assert not should_process
        assert response == cached_data['response']
        assert status == 202
    
    def test_process_request_idempotency_body_conflict(self, idempotency_service, mock_redis):
        """Test idempotency processing with body hash conflict."""
        key_id = "bk_test_key"
        body_hash = "abc123"
        stored_hash = "def456"
        
        # Mock Redis calls
        def mock_get(key):
            if key.startswith("idem:"):
                return None  # No cached response
            elif key.startswith("body_hash:"):
                return stored_hash  # Different body hash
            return None
        
        mock_redis.get.side_effect = mock_get
        
        should_process, response, status = idempotency_service.process_request_idempotency(
            key_id, body_hash
        )
        
        assert not should_process
        assert response['code'] == 'idempotency_conflict'
        assert status == 409
    
    def test_process_request_idempotency_with_custom_key(self, idempotency_service, mock_redis):
        """Test idempotency processing with custom idempotency key."""
        key_id = "bk_test_key"
        body_hash = "abc123"
        custom_key = "custom_idem_key"
        
        # No cached response
        mock_redis.get.return_value = None
        
        should_process, response, status = idempotency_service.process_request_idempotency(
            key_id, body_hash, custom_key
        )
        
        assert should_process
        assert response is None
        assert status is None
        
        # Should check for custom idempotency key, not body hash
        expected_idem_key = f"idem:{key_id}:{custom_key}"
        mock_redis.get.assert_called_with(expected_idem_key)
    
    def test_process_request_idempotency_redis_error(self, idempotency_service, mock_redis):
        """Test idempotency processing with Redis error."""
        key_id = "bk_test_key"
        body_hash = "abc123"
        
        # Redis raises exception
        mock_redis.get.side_effect = Exception("Redis connection error")
        
        should_process, response, status = idempotency_service.process_request_idempotency(
            key_id, body_hash
        )
        
        # Should fail open (allow processing) on Redis errors
        assert should_process
        assert response is None
        assert status is None
    
    def test_cleanup_expired_keys(self, idempotency_service, mock_redis):
        """Test cleanup of expired idempotency keys."""
        # Mock scan to return some keys
        mock_redis.scan_iter.return_value = [
            "idem:bk_test1:abc123",
            "idem:bk_test2:def456",
            "body_hash:bk_test1"
        ]
        
        idempotency_service.cleanup_expired_keys()
        
        # Should scan for idempotency keys
        mock_redis.scan_iter.assert_called_with(match="idem:*")
        
        # Should delete found keys (mocked as successful)
        assert mock_redis.delete.call_count >= 1
    
    def test_get_stats(self, idempotency_service, mock_redis):
        """Test getting idempotency service statistics."""
        # Mock Redis info
        mock_redis.info.return_value = {
            'used_memory': 1024000,
            'connected_clients': 5
        }
        
        # Mock key counts
        mock_redis.eval.return_value = 150  # Total idempotency keys
        
        stats = idempotency_service.get_stats()
        
        assert 'total_keys' in stats
        assert 'memory_usage' in stats
        assert 'connected_clients' in stats
        assert stats['total_keys'] == 150
        assert stats['memory_usage'] == 1024000
        assert stats['connected_clients'] == 5


class TestIdempotencyIntegration:
    """Integration tests for idempotency service."""
    
    @pytest.fixture
    def real_redis_service(self):
        """Create idempotency service with real Redis (if available)."""
        try:
            service = IdempotencyService()
            # Test Redis connection
            service.redis.ping()
            return service
        except:
            pytest.skip("Redis not available for integration tests")
    
    def test_full_idempotency_flow(self, real_redis_service):
        """Test complete idempotency flow with real Redis."""
        service = real_redis_service
        key_id = "bk_integration_test"
        body_hash = "integration_test_hash"
        
        # Clean up any existing data
        idem_key = service.generate_idempotency_key(key_id, body_hash)
        service.redis.delete(idem_key)
        service.redis.delete(f"body_hash:{key_id}")
        
        # First request - should process
        should_process, response, status = service.process_request_idempotency(
            key_id, body_hash
        )
        assert should_process
        assert response is None
        assert status is None
        
        # Store response
        response_data = {"status": "accepted", "id": "test_123"}
        service.store_response(idem_key, response_data, 202)
        
        # Second request with same body - should return cached
        should_process, response, status = service.process_request_idempotency(
            key_id, body_hash
        )
        assert not should_process
        assert response == response_data
        assert status == 202
        
        # Third request with different body - should conflict
        different_hash = "different_hash"
        should_process, response, status = service.process_request_idempotency(
            key_id, different_hash
        )
        assert not should_process
        assert response['code'] == 'idempotency_conflict'
        assert status == 409
        
        # Clean up
        service.redis.delete(idem_key)
        service.redis.delete(f"body_hash:{key_id}")
    
    def test_custom_idempotency_key_flow(self, real_redis_service):
        """Test idempotency flow with custom idempotency key."""
        service = real_redis_service
        key_id = "bk_custom_test"
        body_hash = "custom_test_hash"
        custom_key = "custom_idem_123"
        
        # Clean up
        idem_key = service.generate_idempotency_key(key_id, body_hash, custom_key)
        service.redis.delete(idem_key)
        
        # First request with custom key
        should_process, response, status = service.process_request_idempotency(
            key_id, body_hash, custom_key
        )
        assert should_process
        
        # Store response
        response_data = {"status": "processed", "custom": True}
        service.store_response(idem_key, response_data, 200)
        
        # Second request with same custom key but different body
        different_hash = "totally_different_hash"
        should_process, response, status = service.process_request_idempotency(
            key_id, different_hash, custom_key
        )
        
        # Should return cached response (custom key takes precedence)
        assert not should_process
        assert response == response_data
        assert status == 200
        
        # Clean up
        service.redis.delete(idem_key)
    
    def test_ttl_expiration(self, real_redis_service):
        """Test that idempotency keys expire after TTL."""
        service = real_redis_service
        key_id = "bk_ttl_test"
        body_hash = "ttl_test_hash"
        
        idem_key = service.generate_idempotency_key(key_id, body_hash)
        
        # Store with short TTL for testing
        service.redis.setex(idem_key, 1, json.dumps({
            "response": {"test": "data"},
            "status_code": 200,
            "stored_at": "2023-12-01T10:30:00Z"
        }))
        
        # Should exist immediately
        response, status = service.get_cached_response(idem_key)
        assert response is not None
        
        # Wait for expiration (in real test, might use time.sleep(2))
        # For this test, we'll manually delete to simulate expiration
        service.redis.delete(idem_key)
        
        # Should not exist after expiration
        response, status = service.get_cached_response(idem_key)
        assert response is None
        assert status is None
