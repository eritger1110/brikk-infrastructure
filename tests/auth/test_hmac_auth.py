"""
Comprehensive test suite for HMAC v1 authentication system.
"""
import pytest
import json
import os
import hashlib
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from flask import Flask, g

from src.services.security_enhanced import HMACSecurityService
from src.models.org import Organization
from src.models.agent import Agent
from src.models.api_key import ApiKey
from src.services.auth_middleware import AuthMiddleware
from src.database import db
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
        db.create_all()
        yield app
        db.drop_all()

class TestHMACSecurityService:
    """Test HMAC security service functionality."""
    
    def test_generate_canonical_string(self):
        """Test canonical string generation."""
        canonical = HMACSecurityService.generate_canonical_string(
            method="POST",
            path="/api/v1/coordination",
            timestamp="2023-12-01T10:30:00Z",
            body_hash="abc123",
            message_id="msg_123"
        )
        
        expected = "POST\n/api/v1/coordination\n2023-12-01T10:30:00Z\nabc123\nmsg_123"
        assert canonical == expected
    
    def test_generate_canonical_string_without_message_id(self):
        """Test canonical string generation without message_id."""
        canonical = HMACSecurityService.generate_canonical_string(
            method="GET",
            path="/api/v1/health",
            timestamp="2023-12-01T10:30:00Z",
            body_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        
        expected = "GET\n/api/v1/health\n2023-12-01T10:30:00Z\ne3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert canonical == expected
    
    def test_compute_body_hash(self):
        """Test body hash computation."""
        body = b'{"message": "test"}'
        hash_result = HMACSecurityService.compute_body_hash(body)
        
        expected = hashlib.sha256(body).hexdigest()
        assert hash_result == expected
    
    def test_sign_canonical_string(self):
        """Test canonical string signing."""
        canonical = "POST\n/api/v1/test\n2023-12-01T10:30:00Z\nabc123"
        secret = "test_secret"
        
        signature = HMACSecurityService.sign_canonical_string(canonical, secret)
        
        # Verify it's a valid hex string
        assert len(signature) == 64  # SHA-256 hex
        assert all(c in '0123456789abcdef' for c in signature)
    
    def test_create_and_verify_signature(self):
        """Test signature creation and verification."""
        method = "POST"
        path = "/api/v1/coordination"
        timestamp = "2023-12-01T10:30:00Z"
        body = b'{"message_id": "msg_123", "data": "test"}'
        secret = "test_secret_key"
        message_id = "msg_123"
        
        # Create signature
        signature = HMACSecurityService.create_signature(
            method, path, timestamp, body, secret, message_id
        )
        
        # Verify signature format
        assert signature.startswith("v1=")
        assert len(signature) == 67  # "v1=" + 64 hex chars
        
        # Verify signature
        is_valid = HMACSecurityService.verify_signature(
            method, path, timestamp, body, secret, signature, message_id
        )
        assert is_valid
    
    def test_verify_signature_invalid(self):
        """Test signature verification with invalid signature."""
        method = "POST"
        path = "/api/v1/coordination"
        timestamp = "2023-12-01T10:30:00Z"
        body = b'{"message_id": "msg_123", "data": "test"}'
        secret = "test_secret_key"
        invalid_signature = "v1=invalid_signature_here"
        
        is_valid = HMACSecurityService.verify_signature(
            method, path, timestamp, body, secret, invalid_signature
        )
        assert not is_valid
    
    def test_parse_rfc3339_timestamp_valid_formats(self):
        """Test RFC3339 timestamp parsing with valid formats."""
        test_cases = [
            "2023-12-01T10:30:00Z",
            "2023-12-01T10:30:00.123Z",
            "2023-12-01T10:30:00+00:00",
            "2023-12-01T10:30:00.123+00:00"
        ]
        
        for timestamp_str in test_cases:
            dt = HMACSecurityService.parse_rfc3339_timestamp(timestamp_str)
            assert dt is not None
            assert dt.tzinfo is not None  # Should be timezone-aware
    
    def test_parse_rfc3339_timestamp_invalid(self):
        """Test RFC3339 timestamp parsing with invalid formats."""
        invalid_timestamps = [
            "2023-12-01 10:30:00",  # Missing T
            "2023/12/01T10:30:00Z",  # Wrong date separator
            "invalid_timestamp",
            "",
            None
        ]
        
        for timestamp_str in invalid_timestamps:
            dt = HMACSecurityService.parse_rfc3339_timestamp(timestamp_str)
            assert dt is None
    
    def test_validate_timestamp_drift_valid(self):
        """Test timestamp drift validation with valid timestamps."""
        # Current time
        now = datetime.now(timezone.utc)
        timestamp_str = now.isoformat().replace('+00:00', 'Z')
        
        is_valid, error = HMACSecurityService.validate_timestamp_drift(timestamp_str)
        assert is_valid
        assert error is None
    
    def test_validate_timestamp_drift_too_old(self):
        """Test timestamp drift validation with old timestamp."""
        # 10 minutes ago (exceeds 5-minute limit)
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        timestamp_str = old_time.isoformat().replace('+00:00', 'Z')
        
        is_valid, error = HMACSecurityService.validate_timestamp_drift(timestamp_str)
        assert not is_valid
        assert "drift" in error.lower()
    
    def test_validate_timestamp_drift_too_future(self):
        """Test timestamp drift validation with future timestamp."""
        # 10 minutes in future (exceeds 5-minute limit)
        future_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        timestamp_str = future_time.isoformat().replace('+00:00', 'Z')
        
        is_valid, error = HMACSecurityService.validate_timestamp_drift(timestamp_str)
        assert not is_valid
        assert "drift" in error.lower()
    
    def test_extract_message_id_from_body(self):
        """Test message ID extraction from JSON body."""
        body = b'{"message_id": "msg_123", "data": "test"}'
        message_id = HMACSecurityService.extract_message_id_from_body(body)
        assert message_id == "msg_123"
    
    def test_extract_message_id_from_body_missing(self):
        """Test message ID extraction when not present."""
        body = b'{"data": "test"}'
        message_id = HMACSecurityService.extract_message_id_from_body(body)
        assert message_id is None
    
    def test_extract_message_id_from_body_invalid_json(self):
        """Test message ID extraction with invalid JSON."""
        body = b'invalid json'
        message_id = HMACSecurityService.extract_message_id_from_body(body)
        assert message_id is None
    
    def test_sanitize_path_for_signing(self):
        """Test path sanitization for consistent signing."""
        test_cases = [
            ("/api/v1/coordination", "/api/v1/coordination"),
            ("/api/v1/coordination?param=value", "/api/v1/coordination"),
            ("api/v1/coordination", "/api/v1/coordination"),
            ("/api/v1/coordination/", "/api/v1/coordination"),
        ]
        
        for input_path, expected in test_cases:
            result = HMACSecurityService.sanitize_path_for_signing(input_path)
            assert result == expected
    
    def test_validate_request_headers_valid(self):
        """Test request header validation with valid headers."""
        headers = {
            'X-Brikk-Key': 'bk_test_key',
            'X-Brikk-Timestamp': '2023-12-01T10:30:00Z',
            'X-Brikk-Signature': 'v1=abc123'
        }
        
        is_valid, error, extracted = HMACSecurityService.validate_request_headers(headers)
        assert is_valid
        assert error is None
        assert extracted['x_brikk_key'] == 'bk_test_key'
        assert extracted['x_brikk_timestamp'] == '2023-12-01T10:30:00Z'
        assert extracted['x_brikk_signature'] == 'v1=abc123'
    
    def test_validate_request_headers_missing(self):
        """Test request header validation with missing headers."""
        headers = {
            'X-Brikk-Key': 'bk_test_key',
            # Missing X-Brikk-Timestamp and X-Brikk-Signature
        }
        
        is_valid, error, extracted = HMACSecurityService.validate_request_headers(headers)
        assert not is_valid
        assert "Missing required header" in error
        assert extracted == {}
    
    def test_constant_time_compare(self):
        """Test constant-time string comparison."""
        # Same strings
        assert HMACSecurityService.constant_time_compare("test", "test")
        
        # Different strings
        assert not HMACSecurityService.constant_time_compare("test", "different")
        
        # Different lengths
        assert not HMACSecurityService.constant_time_compare("test", "testing")
    
    def test_create_auth_context(self):
        """Test authentication context creation."""
        context = HMACSecurityService.create_auth_context(
            organization_id=1,
            agent_id=2,
            key_id="bk_test_key",
            scopes='["coordination:write", "agents:read"]'
        )
        
        assert context['organization_id'] == 1
        assert context['agent_id'] == 2
        assert context['key_id'] == "bk_test_key"
        assert context['scopes'] == ["coordination:write", "agents:read"]
        assert 'authenticated_at' in context
        assert 'request_id' in context
    
    def test_hash_for_idempotency(self):
        """Test idempotency key generation."""
        key_id = "bk_very_long_key_id_for_testing"
        body_hash = "abcdef1234567890abcdef1234567890abcdef1234567890"
        
        idem_key = HMACSecurityService.hash_for_idempotency(key_id, body_hash)
        
        assert idem_key.startswith("idem:")
        assert len(idem_key.split(':')) == 3
        # Should truncate long IDs
        assert len(idem_key.split(':')[1]) <= 16
        assert len(idem_key.split(':')[2]) <= 16
    
    def test_create_error_response(self):
        """Test error response creation."""
        error = HMACSecurityService.create_error_response(
            "test_error", "Test error message", "req_123"
        )
        
        assert error['code'] == "test_error"
        assert error['message'] == "Test error message"
        assert error['request_id'] == "req_123"
    
    def test_create_error_response_auto_request_id(self):
        """Test error response creation with auto-generated request ID."""
        error = HMACSecurityService.create_error_response(
            "test_error", "Test error message"
        )
        
        assert error['code'] == "test_error"
        assert error['message'] == "Test error message"
        assert 'request_id' in error
        assert error['request_id'].startswith('req_')


class TestAuthMiddleware:
    """Test authentication middleware functionality."""
    
    @pytest.fixture
    def auth_middleware(self):
        """Create auth middleware instance."""
        return AuthMiddleware()
    
    def test_is_feature_enabled_default_false(self, auth_middleware):
        """Test feature flag checking with default false."""
        with patch.dict(os.environ, {}, clear=True):
            assert not auth_middleware.is_feature_enabled('TEST_FLAG', False)
    
    def test_is_feature_enabled_default_true(self, auth_middleware):
        """Test feature flag checking with default true."""
        with patch.dict(os.environ, {}, clear=True):
            assert auth_middleware.is_feature_enabled('TEST_FLAG', True)
    
    def test_is_feature_enabled_env_true(self, auth_middleware):
        """Test feature flag checking with environment variable true."""
        with patch.dict(os.environ, {'TEST_FLAG': 'true'}):
            assert auth_middleware.is_feature_enabled('TEST_FLAG', False)
    
    def test_is_feature_enabled_env_false(self, auth_middleware):
        """Test feature flag checking with environment variable false."""
        with patch.dict(os.environ, {'TEST_FLAG': 'false'}):
            assert not auth_middleware.is_feature_enabled('TEST_FLAG', True)
    
    @patch('src.services.auth_middleware.request')
    def test_authenticate_request_feature_disabled(self, mock_request, app: Flask, auth_middleware):
        """Test authentication when per-org keys feature is disabled."""
        with app.test_request_context():
            with patch.dict(os.environ, {'BRIKK_FEATURE_PER_ORG_KEYS': 'false'}):
                success, error, status = auth_middleware.authenticate_request()
                assert success
                assert error is None
                assert status is None
    
    @patch('src.services.auth_middleware.request')
    def test_authenticate_request_missing_headers(self, mock_request, app: Flask, auth_middleware):
        """Test authentication with missing headers."""
        mock_request.headers = {}
        
        with app.test_request_context():
            with patch.dict(os.environ, {'BRIKK_FEATURE_PER_ORG_KEYS': 'true'}):
                success, error, status = auth_middleware.authenticate_request()
                assert not success
                assert error['code'] == 'protocol_error'
                assert status == 400
    
    @patch('src.services.auth_middleware.request')
    def test_authenticate_request_invalid_timestamp(self, mock_request, app: Flask, auth_middleware):
        """Test authentication with invalid timestamp."""
        # 10 minutes ago (exceeds drift limit)
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        timestamp_str = old_time.isoformat().replace('+00:00', 'Z')
        
        mock_request.headers = {
            'X-Brikk-Key': 'bk_test_key',
            'X-Brikk-Timestamp': timestamp_str,
            'X-Brikk-Signature': 'v1=abc123'
        }
        
        with app.test_request_context():
            with patch.dict(os.environ, {'BRIKK_FEATURE_PER_ORG_KEYS': 'true'}):
                success, error, status = auth_middleware.authenticate_request()
                assert not success
                assert error['code'] == 'timestamp_error'
                assert status == 401
    
    @patch('src.models.api_key.ApiKey.get_by_key_id')
    @patch('src.services.auth_middleware.request')
    def test_authenticate_request_invalid_api_key(self, mock_request, mock_get_key, app: Flask, auth_middleware):
        """Test authentication with invalid API key."""
        mock_get_key.return_value = None
        
        now = datetime.now(timezone.utc)
        timestamp_str = now.isoformat().replace('+00:00', 'Z')
        
        mock_request.headers = {
            'X-Brikk-Key': 'bk_invalid_key',
            'X-Brikk-Timestamp': timestamp_str,
            'X-Brikk-Signature': 'v1=abc123'
        }
        
        with app.test_request_context():
            with patch.dict(os.environ, {'BRIKK_FEATURE_PER_ORG_KEYS': 'true'}):
                success, error, status = auth_middleware.authenticate_request()
                assert not success
                assert error['code'] == 'invalid_api_key'
                assert status == 401
    
    @patch('src.services.auth_middleware.request')
    def test_check_idempotency_feature_disabled(self, mock_request, app: Flask, auth_middleware):
        """Test idempotency check when feature is disabled."""
        with app.test_request_context():
            with patch.dict(os.environ, {'BRIKK_IDEM_ENABLED': 'false'}):
                success, response, status = auth_middleware.check_idempotency()
                assert success
                assert response is None
                assert status is None
    
    @patch('src.services.auth_middleware.request')
    def test_check_idempotency_no_auth(self, mock_request, app: Flask, auth_middleware):
        """Test idempotency check without authentication context."""
        with app.test_request_context():
            with patch.dict(os.environ, {'BRIKK_IDEM_ENABLED': 'true'}):
                # No auth context on g
                if hasattr(g, 'auth_context'):
                    del g.auth_context
                
                success, response, status = auth_middleware.check_idempotency()
                assert not success
                assert response['code'] == 'internal_error'
                assert status == 500
    
    @patch('src.services.idempotency.IdempotencyService.process_request_idempotency')
    @patch('src.services.auth_middleware.request')
    def test_check_idempotency_success(self, mock_request, mock_process, app: Flask, auth_middleware):
        """Test successful idempotency check."""
        mock_process.return_value = (True, None, None)
        
        with app.test_request_context():
            with patch.dict(os.environ, {'BRIKK_IDEM_ENABLED': 'true'}):
                g.auth_context = {'key_id': 'bk_test_key'}
                mock_request.get_data.return_value = b'{"test": "body"}'
                
                success, response, status = auth_middleware.check_idempotency()
                assert success
                assert response is None
                assert status is None
    
    @patch('src.services.idempotency.IdempotencyService.process_request_idempotency')
    @patch('src.services.auth_middleware.request')
    def test_check_idempotency_replay(self, mock_request, mock_process, app: Flask, auth_middleware):
        """Test idempotency check with replayed request."""
        replayed_response = ({ 'message': 'replayed'}, 200)
        mock_process.return_value = (False, replayed_response, 200)
        
        with app.test_request_context():
            with patch.dict(os.environ, {'BRIKK_IDEM_ENABLED': 'true'}):
                g.auth_context = {'key_id': 'bk_test_key'}
                mock_request.get_data.return_value = b'{"test": "body"}'
                
                success, response, status = auth_middleware.check_idempotency()
                assert not success
                assert response == replayed_response
                assert status == 200
    
    @patch('src.services.auth_middleware.request')
    def test_set_auth_context(self, mock_request, app: Flask, auth_middleware):
        """Test setting authentication context on Flask's g."""
        auth_context = {'organization_id': 1, 'agent_id': 2}
        
        with app.test_request_context():
            auth_middleware.set_auth_context(auth_context)
            assert hasattr(g, 'auth_context')
            assert g.auth_context == auth_context
    
    @patch('src.services.auth_middleware.request')
    def test_log_auth_result_success(self, mock_request, app: Flask, auth_middleware):
        """Test logging successful authentication."""
        with app.test_request_context():
            with patch.object(auth_middleware.logger, 'info') as mock_log:
                g.auth_context = {'key_id': 'bk_test_key'}
                auth_middleware.log_auth_result(True)
                
                mock_log.assert_called_once()
                log_message = mock_log.call_args[0][0]
                assert "Authentication successful" in log_message
                assert "key_id=bk_test_key" in log_message
    
    @patch('src.services.auth_middleware.request')
    def test_log_auth_result_failure(self, mock_request, app: Flask, auth_middleware):
        """Test logging failed authentication."""
        with app.test_request_context():
            with patch.object(auth_middleware.logger, 'warning') as mock_log:
                error = {'code': 'test_error', 'message': 'Test error'}
                auth_middleware.log_auth_result(False, error=error)
                
                mock_log.assert_called_once()
                log_message = mock_log.call_args[0][0]
                assert "Authentication failed" in log_message
                assert "error=test_error" in log_message

