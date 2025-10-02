"""
Comprehensive test suite for HMAC v1 authentication system.
"""
import pytest
import json
import os
import hashlib
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from src.services.security_enhanced import HMACSecurityService
from src.models.org import Organization
from src.models.agent import Agent
from src.models.api_key import ApiKey
from src.services.auth_middleware import AuthMiddleware
from src.database.db import db


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
    def app_context(self):
        """Create Flask app context for testing."""
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        with app.app_context():
            yield app
    
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
    def test_authenticate_request_feature_disabled(self, mock_request, auth_middleware):
        """Test authentication when per-org keys feature is disabled."""
        with patch.dict(os.environ, {'BRIKK_FEATURE_PER_ORG_KEYS': 'false'}):
            success, error, status = auth_middleware.authenticate_request()
            assert success
            assert error is None
            assert status is None
    
    @patch('src.services.auth_middleware.request')
    def test_authenticate_request_missing_headers(self, mock_request, auth_middleware):
        """Test authentication with missing headers."""
        mock_request.headers = {}
        
        with patch.dict(os.environ, {'BRIKK_FEATURE_PER_ORG_KEYS': 'true'}):
            success, error, status = auth_middleware.authenticate_request()
            assert not success
            assert error['code'] == 'protocol_error'
            assert status == 400
    
    @patch('src.services.auth_middleware.request')
    def test_authenticate_request_invalid_timestamp(self, mock_request, auth_middleware):
        """Test authentication with invalid timestamp."""
        # 10 minutes ago (exceeds drift limit)
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        timestamp_str = old_time.isoformat().replace('+00:00', 'Z')
        
        mock_request.headers = {
            'X-Brikk-Key': 'bk_test_key',
            'X-Brikk-Timestamp': timestamp_str,
            'X-Brikk-Signature': 'v1=abc123'
        }
        
        with patch.dict(os.environ, {'BRIKK_FEATURE_PER_ORG_KEYS': 'true'}):
            success, error, status = auth_middleware.authenticate_request()
            assert not success
            assert error['code'] == 'timestamp_error'
            assert status == 401
    
    @patch('src.services.auth_middleware.request')
    @patch('src.models.api_key.ApiKey.get_by_key_id')
    def test_authenticate_request_invalid_api_key(self, mock_get_key, mock_request, auth_middleware):
        """Test authentication with invalid API key."""
        mock_get_key.return_value = None
        
        now = datetime.now(timezone.utc)
        timestamp_str = now.isoformat().replace('+00:00', 'Z')
        
        mock_request.headers = {
            'X-Brikk-Key': 'bk_invalid_key',
            'X-Brikk-Timestamp': timestamp_str,
            'X-Brikk-Signature': 'v1=abc123'
        }
        
        with patch.dict(os.environ, {'BRIKK_FEATURE_PER_ORG_KEYS': 'true'}):
            success, error, status = auth_middleware.authenticate_request()
            assert not success
            assert error['code'] == 'invalid_api_key'
            assert status == 401
    
    @patch('src.services.auth_middleware.request')
    @patch('src.services.auth_middleware.g')
    def test_check_idempotency_feature_disabled(self, mock_g, mock_request, auth_middleware):
        """Test idempotency check when feature is disabled."""
        with patch.dict(os.environ, {'BRIKK_IDEM_ENABLED': 'false'}):
            success, response, status = auth_middleware.check_idempotency()
            assert success
            assert response is None
            assert status is None
    
    @patch('src.services.auth_middleware.request')
    @patch('src.services.auth_middleware.g')
    def test_check_idempotency_no_auth(self, mock_g, mock_request, auth_middleware):
        """Test idempotency check without authentication context."""
        # Mock g without api_key attribute
        mock_g.configure_mock(**{})
        del mock_g.api_key  # Ensure api_key doesn't exist
        
        with patch.dict(os.environ, {'BRIKK_IDEM_ENABLED': 'true'}):
            success, response, status = auth_middleware.check_idempotency()
            assert success
            assert response is None
            assert status is None


class TestIntegrationScenarios:
    """Integration tests for complete authentication scenarios."""
    
    @pytest.fixture
    def app(self):
        """Create Flask app for integration testing."""
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize database
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def test_org(self, app):
        """Create test organization."""
        with app.app_context():
            org = Organization(
                name="Test Organization",
                slug="test-org",
                description="Test organization for authentication tests"
            )
            db.session.add(org)
            db.session.commit()
            return org
    
    @pytest.fixture
    def test_agent(self, app, test_org):
        """Create test agent."""
        with app.app_context():
            agent = Agent(
                agent_id="test-agent-001",
                name="Test Agent",
                organization_id=test_org.id
            )
            db.session.add(agent)
            db.session.commit()
            return agent
    
    @pytest.fixture
    def test_api_key(self, app, test_org, test_agent):
        """Create test API key."""
        with app.app_context():
            with patch.dict(os.environ, {'BRIKK_ENCRYPTION_KEY': 'test_key_32_bytes_long_for_fernet'}):
                api_key, secret = ApiKey.create_api_key(
                    organization_id=test_org.id,
                    name="Test API Key",
                    agent_id=test_agent.id
                )
                return api_key, secret
    
    def test_valid_hmac_request(self, app, client, test_api_key):
        """Test valid HMAC authenticated request."""
        api_key, secret = test_api_key
        
        # Prepare request
        body = json.dumps({
            "version": "1.0",
            "message_id": "01234567-89ab-cdef-0123-456789abcdef",
            "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "type": "message",
            "sender": {"agent_id": "test-sender"},
            "recipient": {"agent_id": "test-recipient"},
            "payload": {"action": "test"}
        })
        
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        # Create HMAC signature
        signature = HMACSecurityService.create_signature(
            method="POST",
            path="/api/v1/coordination",
            timestamp=timestamp,
            body=body.encode(),
            secret=secret,
            message_id="01234567-89ab-cdef-0123-456789abcdef"
        )
        
        headers = {
            'Content-Type': 'application/json',
            'X-Brikk-Key': api_key.key_id,
            'X-Brikk-Timestamp': timestamp,
            'X-Brikk-Signature': signature
        }
        
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'true',
            'BRIKK_IDEM_ENABLED': 'true',
            'BRIKK_ALLOW_UUID4': 'false'
        }):
            # Mock the coordination endpoint to test authentication
            @app.route('/api/v1/coordination', methods=['POST'])
            def test_coordination():
                from src.services.auth_middleware import AuthMiddleware
                auth_middleware = AuthMiddleware()
                
                # Test authentication
                auth_success, auth_error, auth_status = auth_middleware.authenticate_request()
                if not auth_success:
                    return auth_error, auth_status
                
                return {"status": "authenticated", "message": "success"}, 200
            
            response = client.post('/api/v1/coordination', 
                                 data=body, 
                                 headers=headers)
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'authenticated'
    
    def test_invalid_signature_request(self, app, client, test_api_key):
        """Test request with invalid HMAC signature."""
        api_key, secret = test_api_key
        
        body = json.dumps({
            "version": "1.0",
            "message_id": "01234567-89ab-cdef-0123-456789abcdef",
            "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "type": "message",
            "sender": {"agent_id": "test-sender"},
            "recipient": {"agent_id": "test-recipient"},
            "payload": {"action": "test"}
        })
        
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        headers = {
            'Content-Type': 'application/json',
            'X-Brikk-Key': api_key.key_id,
            'X-Brikk-Timestamp': timestamp,
            'X-Brikk-Signature': 'v1=invalid_signature_here'
        }
        
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'true',
            'BRIKK_IDEM_ENABLED': 'true'
        }):
            @app.route('/api/v1/coordination', methods=['POST'])
            def test_coordination():
                from src.services.auth_middleware import AuthMiddleware
                auth_middleware = AuthMiddleware()
                
                auth_success, auth_error, auth_status = auth_middleware.authenticate_request()
                if not auth_success:
                    return auth_error, auth_status
                
                return {"status": "authenticated"}, 200
            
            response = client.post('/api/v1/coordination', 
                                 data=body, 
                                 headers=headers)
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['code'] == 'invalid_signature'
    
    def test_timestamp_drift_request(self, app, client, test_api_key):
        """Test request with timestamp drift exceeding limits."""
        api_key, secret = test_api_key
        
        body = json.dumps({
            "version": "1.0",
            "message_id": "01234567-89ab-cdef-0123-456789abcdef",
            "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "type": "message",
            "sender": {"agent_id": "test-sender"},
            "recipient": {"agent_id": "test-recipient"},
            "payload": {"action": "test"}
        })
        
        # Use timestamp 10 minutes ago (exceeds 5-minute limit)
        old_timestamp = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat().replace('+00:00', 'Z')
        
        signature = HMACSecurityService.create_signature(
            method="POST",
            path="/api/v1/coordination",
            timestamp=old_timestamp,
            body=body.encode(),
            secret=secret,
            message_id="01234567-89ab-cdef-0123-456789abcdef"
        )
        
        headers = {
            'Content-Type': 'application/json',
            'X-Brikk-Key': api_key.key_id,
            'X-Brikk-Timestamp': old_timestamp,
            'X-Brikk-Signature': signature
        }
        
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'true',
            'BRIKK_IDEM_ENABLED': 'true'
        }):
            @app.route('/api/v1/coordination', methods=['POST'])
            def test_coordination():
                from src.services.auth_middleware import AuthMiddleware
                auth_middleware = AuthMiddleware()
                
                auth_success, auth_error, auth_status = auth_middleware.authenticate_request()
                if not auth_success:
                    return auth_error, auth_status
                
                return {"status": "authenticated"}, 200
            
            response = client.post('/api/v1/coordination', 
                                 data=body, 
                                 headers=headers)
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['code'] == 'timestamp_error'
            assert 'drift' in data['message'].lower()
