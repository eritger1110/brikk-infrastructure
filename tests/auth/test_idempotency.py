'''
Test suite for Redis-based idempotency service.
'''
import pytest
import json
from unittest.mock import patch, MagicMock
from flask import Flask

from src.services.idempotency import IdempotencyService
from src.factory import create_app

@pytest.fixture(scope="function")
def app() -> Flask:
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret-key"
    })
    with app.app_context():
        yield app

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
        
        assert idem_key == f"idem:{key_id}:{body_hash}:{custom_key}"
    
    def test_generate_idempotency_key_without_custom_key(self, idempotency_service):
        """Test idempotency key generation without custom key."""
        key_id = "bk_test_key"
        body_hash = "abc123def456"
        
        idem_key = idempotency_service.generate_idempotency_key(
            key_id, body_hash
        )
        
        expected = f"idem:{key_id[:16]}:{body_hash[:16]}"
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
        assert stored_data['response_data'] == response_data
        assert stored_data['status_code'] == status_code
        assert 'created_at' in stored_data
    
    def test_get_cached_response_exists(self, app: Flask, idempotency_service, mock_redis):
        """Test getting cached response when it exists."""
        idem_key = "idem:bk_test:abc123"
        cached_data = {
            "response_data": {"status": "accepted", "id": "123"},
            "status_code": 202,
            "stored_at": "2023-12-01T10:30:00Z"
        }
        
        mock_redis.get.return_value = json.dumps(cached_data)
        
        with app.app_context():
            response, status_code = idempotency_service.get_cached_response(idem_key)
        
        assert response == cached_data['response_data']
        assert status_code == 202
        mock_redis.get.assert_called_once_with(idem_key)
    
    def test_get_cached_response_not_exists(self, app: Flask, idempotency_service, mock_redis):
        """Test getting cached response when it doesn't exist."""
        idem_key = "idem:bk_test:abc123"
        mock_redis.get.return_value = None
        
        with app.app_context():
            response, status_code = idempotency_service.get_cached_response(idem_key)
        
        assert response is None
        assert status_code is None
        mock_redis.get.assert_called_once_with(idem_key)
    
    def test_get_cached_response_invalid_json(self, app: Flask, idempotency_service, mock_redis):
        """Test getting cached response with invalid JSON."""
        idem_key = "idem:bk_test:abc123"
        mock_redis.get.return_value = "invalid json"
        
        with app.app_context():
            response, status_code = idempotency_service.get_cached_response(idem_key)
        
        assert response is None
        assert status_code is None

    def test_process_request_idempotency_first_request(self, app: Flask, idempotency_service, mock_redis):
        """Test idempotency processing for first request."""
        key_id = "bk_test_key"
        body_hash = "abc123"
        
        # No cached response
        mock_redis.get.return_value = None
        
        with app.app_context():
            should_process, response, status = idempotency_service.process_request_idempotency(
                key_id, body_hash
            )
        
        assert should_process
        assert response is None
        assert status is None

    def test_process_request_idempotency_cached_response(self, app: Flask, idempotency_service, mock_redis):
        """Test idempotency processing with cached response."""
        key_id = "bk_test_key"
        body_hash = "abc123"
        
        cached_data = {
            "response_data": {"status": "accepted", "id": "123"},
            "status_code": 202,
            "stored_at": "2023-12-01T10:30:00Z"
        }
        
        # Mock Redis calls
        def mock_get(key):
            if key.startswith("idem:"):
                return json.dumps(cached_data)
            return None

        mock_redis.get.side_effect = mock_get

        with app.app_context():
            should_process, response, status = idempotency_service.process_request_idempotency(
                key_id, body_hash
            )
        
        assert not should_process
        assert response == cached_data['response_data']
        assert status == 202

    def test_process_request_idempotency_body_conflict(self, app: Flask, idempotency_service, mock_redis):
        """Test idempotency processing with body hash conflict."""
        key_id = "bk_test_key"
        body_hash = "abc123"
        custom_key = "custom_idem_key"

        # Mock Redis calls
        def mock_get(key):
            if "custom" in key:
                 return json.dumps({
                    "response_data": {"status": "processed", "custom": True},
                    "status_code": 200,
                    "stored_at": "2023-12-01T10:30:00Z"
                })
            return None

        mock_redis.get.side_effect = mock_get

        with app.app_context():
            should_process, response, status = idempotency_service.process_request_idempotency(
                key_id, body_hash, custom_key
            )
        
        assert not should_process
        assert response['code'] == 'idempotency_conflict'
        assert status == 409

    def test_process_request_idempotency_with_custom_key(self, app: Flask, idempotency_service, mock_redis):
        """Test idempotency processing with custom idempotency key."""
        key_id = "bk_test_key"
        body_hash = "abc123"
        custom_key = "custom_idem_key"
        
        # No cached response
        mock_redis.get.return_value = None
        
        with app.app_context():
            should_process, response, status = idempotency_service.process_request_idempotency(
                key_id, body_hash, custom_key
            )
        
        assert should_process
        assert response is None
        assert status is None
        
        # Should check for custom idempotency key
        expected_idem_key = idempotency_service.generate_idempotency_key(key_id, "", custom_key)
        mock_redis.get.assert_called_with(expected_idem_key)

    def test_process_request_idempotency_redis_error(self, app: Flask, idempotency_service, mock_redis):
        """Test idempotency processing with Redis error."""
        key_id = "bk_test_key"
        body_hash = "abc123"
        
        # Redis raises exception
        mock_redis.get.side_effect = Exception("Redis connection error")
        
        with app.app_context():
            should_process, response, status = idempotency_service.process_request_idempotency(
                key_id, body_hash
            )
        
        # Should fail open (allow processing) on Redis errors
        assert should_process
        assert response is None
        assert status is None

