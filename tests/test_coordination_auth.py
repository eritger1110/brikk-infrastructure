"""
Test suite for coordination endpoint authentication and idempotency.

Tests the full security layer integration including:
- HMAC v1 authentication
- Timestamp drift checking
- Redis idempotency
- Feature flag behavior
- Error handling
"""

import os
import json
import hashlib
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from src.main import create_app
from src.models.api_key import ApiKey
from src.models.org import Organization
from src.services.security_enhanced import HMACSecurityService
from src.services.idempotency import IdempotencyService


class TestCoordinationAuth:
    """Test coordination endpoint authentication."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
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
    
    @pytest.fixture
    def mock_api_key(self):
        """Create mock API key."""
        api_key = MagicMock(spec=ApiKey)
        api_key.key_id = "test-key-id"
        api_key.organization_id = "test-org-id"
        api_key.agent_id = "test-agent-id"
        api_key.is_valid.return_value = True
        api_key.decrypt_secret.return_value = "test-secret-key"
        api_key.update_usage = MagicMock()
        return api_key
    
    def create_hmac_headers(self, method: str, path: str, body: bytes, 
                          secret: str, message_id: str = "", 
                          timestamp: str = None) -> dict:
        """Create valid HMAC headers for testing."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()
        
        signature = HMACSecurityService.generate_signature(
            method=method,
            path=path,
            timestamp=timestamp,
            body=body,
            secret=secret,
            message_id=message_id
        )
        
        return {
            'X-Brikk-Key': 'test-key-id',
            'X-Brikk-Timestamp': timestamp,
            'X-Brikk-Signature': signature,
            'Content-Type': 'application/json'
        }
    
    def test_coordination_endpoint_flags_off(self, client, valid_envelope):
        """Test coordination endpoint with all feature flags OFF."""
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'false',
            'BRIKK_IDEM_ENABLED': 'false'
        }):
            response = client.post(
                '/api/v1/coordination',
                data=json.dumps(valid_envelope),
                headers={'Content-Type': 'application/json'}
            )
            
            assert response.status_code == 202
            data = response.get_json()
            assert data['status'] == 'accepted'
            assert data['echo']['message_id'] == valid_envelope['message_id']
            assert 'auth' not in data  # No auth context when flags off
    
    @patch('src.models.api_key.ApiKey.query')
    def test_coordination_endpoint_valid_hmac(self, mock_query, client, valid_envelope, mock_api_key):
        """Test coordination endpoint with valid HMAC authentication."""
        mock_query.filter_by.return_value.first.return_value = mock_api_key
        
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'true',
            'BRIKK_IDEM_ENABLED': 'false'
        }):
            body = json.dumps(valid_envelope).encode()
            headers = self.create_hmac_headers(
                'POST', '/api/v1/coordination', body, 'test-secret-key',
                valid_envelope['message_id']
            )
            
            response = client.post(
                '/api/v1/coordination',
                data=body,
                headers=headers
            )
            
            assert response.status_code == 202
            data = response.get_json()
            assert data['status'] == 'accepted'
            assert data['echo']['message_id'] == valid_envelope['message_id']
            assert 'auth' in data
            assert data['auth']['organization_id'] == 'test-org-id'
            assert data['auth']['agent_id'] == 'test-agent-id'
            
            # Verify API key usage was updated
            mock_api_key.update_usage.assert_called_once_with(success=True)
    
    def test_coordination_endpoint_missing_headers(self, client, valid_envelope):
        """Test coordination endpoint with missing HMAC headers."""
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'true',
            'BRIKK_IDEM_ENABLED': 'false'
        }):
            response = client.post(
                '/api/v1/coordination',
                data=json.dumps(valid_envelope),
                headers={'Content-Type': 'application/json'}
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['code'] == 'protocol_error'
            assert 'Missing required headers' in data['message']
            assert 'request_id' in data
    
    @patch('src.models.api_key.ApiKey.query')
    def test_coordination_endpoint_invalid_api_key(self, mock_query, client, valid_envelope):
        """Test coordination endpoint with invalid API key."""
        mock_query.filter_by.return_value.first.return_value = None
        
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'true',
            'BRIKK_IDEM_ENABLED': 'false'
        }):
            body = json.dumps(valid_envelope).encode()
            headers = self.create_hmac_headers(
                'POST', '/api/v1/coordination', body, 'test-secret-key'
            )
            
            response = client.post(
                '/api/v1/coordination',
                data=body,
                headers=headers
            )
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['code'] == 'unauthorized'
            assert 'Invalid or disabled API key' in data['message']
    
    @patch('src.models.api_key.ApiKey.query')
    def test_coordination_endpoint_invalid_signature(self, mock_query, client, valid_envelope, mock_api_key):
        """Test coordination endpoint with invalid HMAC signature."""
        mock_query.filter_by.return_value.first.return_value = mock_api_key
        
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'true',
            'BRIKK_IDEM_ENABLED': 'false'
        }):
            body = json.dumps(valid_envelope).encode()
            headers = {
                'X-Brikk-Key': 'test-key-id',
                'X-Brikk-Timestamp': datetime.now(timezone.utc).isoformat(),
                'X-Brikk-Signature': 'invalid-signature',
                'Content-Type': 'application/json'
            }
            
            response = client.post(
                '/api/v1/coordination',
                data=body,
                headers=headers
            )
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['code'] == 'unauthorized'
            assert 'Invalid HMAC signature' in data['message']
            
            # Verify failed usage was recorded
            mock_api_key.update_usage.assert_called_once_with(success=False)
    
    @patch('src.models.api_key.ApiKey.query')
    def test_coordination_endpoint_timestamp_drift(self, mock_query, client, valid_envelope, mock_api_key):
        """Test coordination endpoint with timestamp outside drift window."""
        mock_query.filter_by.return_value.first.return_value = mock_api_key
        
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'true',
            'BRIKK_IDEM_ENABLED': 'false'
        }):
            # Create timestamp 400 seconds in the past (outside '+/-300s window)
            old_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=400)).isoformat()
            
            body = json.dumps(valid_envelope).encode()
            headers = self.create_hmac_headers(
                'POST', '/api/v1/coordination', body, 'test-secret-key',
                valid_envelope['message_id'], old_timestamp
            )
            
            response = client.post(
                '/api/v1/coordination',
                data=body,
                headers=headers
            )
            
            assert response.status_code == 401
            data = response.get_json()
            assert data['code'] == 'unauthorized'
            assert 'timestamp outside acceptable drift' in data['message']
            
            # Verify failed usage was recorded
            mock_api_key.update_usage.assert_called_once_with(success=False)
    
    @patch('src.models.api_key.ApiKey.query')
    @patch('src.services.idempotency.IdempotencyService.process_request_idempotency')
    def test_coordination_endpoint_idempotent_replay(self, mock_idempotency, mock_query, 
                                                   client, valid_envelope, mock_api_key):
        """Test coordination endpoint with idempotent replay (same request)."""
        mock_query.filter_by.return_value.first.return_value = mock_api_key
        
        # Mock idempotency service to return cached response
        cached_response = {
            "status": "accepted",
            "echo": {"message_id": valid_envelope['message_id']}
        }
        mock_idempotency.return_value = (False, cached_response, 202)
        
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'true',
            'BRIKK_IDEM_ENABLED': 'true'
        }):
            body = json.dumps(valid_envelope).encode()
            headers = self.create_hmac_headers(
                'POST', '/api/v1/coordination', body, 'test-secret-key',
                valid_envelope['message_id']
            )
            
            response = client.post(
                '/api/v1/coordination',
                data=body,
                headers=headers
            )
            
            assert response.status_code == 202
            data = response.get_json()
            assert data['status'] == 'accepted'
            assert data['echo']['message_id'] == valid_envelope['message_id']
    
    @patch('src.models.api_key.ApiKey.query')
    @patch('src.services.idempotency.IdempotencyService.process_request_idempotency')
    def test_coordination_endpoint_idempotency_conflict(self, mock_idempotency, mock_query,
                                                      client, valid_envelope, mock_api_key):
        """Test coordination endpoint with idempotency conflict (same key, different body)."""
        mock_query.filter_by.return_value.first.return_value = mock_api_key
        
        # Mock idempotency service to return conflict
        mock_idempotency.return_value = (False, None, 409)
        
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'true',
            'BRIKK_IDEM_ENABLED': 'true'
        }):
            body = json.dumps(valid_envelope).encode()
            headers = self.create_hmac_headers(
                'POST', '/api/v1/coordination', body, 'test-secret-key',
                valid_envelope['message_id']
            )
            
            response = client.post(
                '/api/v1/coordination',
                data=body,
                headers=headers
            )
            
            assert response.status_code == 409
            data = response.get_json()
            assert data['code'] == 'idempotency_conflict'
            assert 'conflicts with previous request' in data['message']
    
    def test_coordination_endpoint_invalid_envelope(self, client):
        """Test coordination endpoint with invalid envelope schema."""
        invalid_envelope = {
            "version": "2.0",  # Invalid version
            "message_id": "invalid-uuid",  # Invalid UUID format
            "ts": "invalid-timestamp",  # Invalid timestamp
            "type": "invalid-type",  # Invalid type
            "sender": {"agent_id": "test"},
            "recipient": {"agent_id": "test"},
            "payload": {},
            "ttl_ms": 200000  # Out of range
        }
        
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'false',
            'BRIKK_IDEM_ENABLED': 'false'
        }):
            response = client.post(
                '/api/v1/coordination',
                data=json.dumps(invalid_envelope),
                headers={'Content-Type': 'application/json'}
            )
            
            assert response.status_code == 422
            data = response.get_json()
            assert data['code'] == 'validation_error'
            assert 'Envelope validation failed' in data['message']
            assert 'details' in data
            assert len(data['details']) > 0
    
    def test_coordination_endpoint_invalid_json(self, client):
        """Test coordination endpoint with invalid JSON."""
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'false',
            'BRIKK_IDEM_ENABLED': 'false'
        }):
            response = client.post(
                '/api/v1/coordination',
                data='invalid json',
                headers={'Content-Type': 'application/json'}
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['code'] == 'protocol_error'
            assert 'Invalid JSON' in data['message']
    
    def test_coordination_health_endpoint(self, client):
        """Test coordination health check endpoint."""
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'true',
            'BRIKK_IDEM_ENABLED': 'true',
            'BRIKK_ALLOW_UUID4': 'false'
        }):
            response = client.get('/api/v1/coordination/health')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'healthy'
            assert data['service'] == 'coordination-api'
            assert data['version'] == '1.0'
            assert 'features' in data
            assert data['features']['per_org_keys'] is True
            assert data['features']['idempotency'] is True
            assert data['features']['uuid4_allowed'] is False
    
    def test_security_headers_present(self, client, valid_envelope):
        """Test that security headers are present in responses."""
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'false',
            'BRIKK_IDEM_ENABLED': 'false'
        }):
            response = client.post(
                '/api/v1/coordination',
                data=json.dumps(valid_envelope),
                headers={'Content-Type': 'application/json'}
            )
            
            assert response.status_code == 202
            
            # Check security headers
            assert 'Strict-Transport-Security' in response.headers
            assert 'X-Content-Type-Options' in response.headers
            assert 'Referrer-Policy' in response.headers
            
            assert response.headers['Strict-Transport-Security'] == 'max-age=31536000; includeSubDomains; preload'
            assert response.headers['X-Content-Type-Options'] == 'nosniff'
            assert response.headers['Referrer-Policy'] == 'no-referrer'
    
    @patch('src.models.api_key.ApiKey.query')
    def test_coordination_endpoint_with_custom_idempotency_key(self, mock_query, client, 
                                                             valid_envelope, mock_api_key):
        """Test coordination endpoint with custom Idempotency-Key header."""
        mock_query.filter_by.return_value.first.return_value = mock_api_key
        
        with patch.dict(os.environ, {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'true',
            'BRIKK_IDEM_ENABLED': 'true'
        }):
            body = json.dumps(valid_envelope).encode()
            headers = self.create_hmac_headers(
                'POST', '/api/v1/coordination', body, 'test-secret-key',
                valid_envelope['message_id']
            )
            headers['Idempotency-Key'] = 'custom-idem-key-123'
            
            with patch('src.services.idempotency.IdempotencyService.process_request_idempotency') as mock_idem:
                mock_idem.return_value = (True, None, None)  # Should process
                
                response = client.post(
                    '/api/v1/coordination',
                    data=body,
                    headers=headers
                )
                
                assert response.status_code == 202
                
                # Verify idempotency service was called with custom key
                mock_idem.assert_called_once()
                call_args = mock_idem.call_args[1]
                assert call_args['custom_idempotency_key'] == 'custom-idem-key-123'


class TestCoordinationAuthIntegration:
    """Integration tests for coordination authentication."""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app with database."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client with database setup."""
        with app.app_context():
            from src.models import db
            db.create_all()
            yield app.test_client()
            db.drop_all()
    
    def test_full_authentication_flow(self, client):
        """Test complete authentication flow with real database."""
        # This would require setting up real database records
        # For now, we'll skip this test in the basic implementation
        pytest.skip("Integration test requires full database setup")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
