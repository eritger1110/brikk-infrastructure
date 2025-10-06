"""
Smoke test for coordination API functionality.

LOCAL DEVELOPMENT ONLY - NOT WIRED TO CI
"""

import pytest
import requests
import json
import uuid
import time
import os
from datetime import datetime, timezone


class TestCoordinationAPI:
    """Test coordination API basic functionality."""
    
    @pytest.fixture(scope="class")
    def base_url(self):
        """Base URL for local Flask app."""
        return "http://localhost:8000"
    
    @pytest.fixture
    def valid_envelope(self):
        """Create a valid envelope for testing."""
        return {
            "version": "1.0",
            "message_id": str(uuid.uuid4()),
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "message",
            "sender": {
                "agent_id": "test-agent-sender",
                "org_id": "test-org"
            },
            "recipient": {
                "agent_id": "test-agent-recipient", 
                "org_id": "test-org"
            },
            "payload": {
                "action": "test",
                "data": "smoke test payload"
            },
            "ttl_ms": 30000
        }
    
    def test_coordination_endpoint_exists(self, base_url):
        """Test that coordination endpoint exists."""
        try:
            response = requests.post(f"{base_url}/api/v1/coordination", timeout=5)
            # Should not be 404 (not found)
            assert response.status_code != 404
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running - start with ./scripts/dev.sh")
    
    def test_content_type_validation(self, base_url, valid_envelope):
        """Test content-type validation."""
        try:
            # Test without content-type header
            response = requests.post(
                f"{base_url}/api/v1/coordination",
                data=json.dumps(valid_envelope),
                timeout=5
            )
            assert response.status_code == 415  # Unsupported Media Type
            
            # Test with wrong content-type
            response = requests.post(
                f"{base_url}/api/v1/coordination",
                data=json.dumps(valid_envelope),
                headers={"Content-Type": "text/plain"},
                timeout=5
            )
            assert response.status_code == 415
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running")
    
    def test_required_headers_validation(self, base_url, valid_envelope):
        """Test required headers validation."""
        try:
            headers = {"Content-Type": "application/json"}
            
            response = requests.post(
                f"{base_url}/api/v1/coordination",
                json=valid_envelope,
                headers=headers,
                timeout=5
            )
            
            # Should fail due to missing required headers
            assert response.status_code == 400
            
            data = response.json()
            assert data["code"] == "protocol_error"
            assert "request_id" in data
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running")
    
    def test_body_size_limit(self, base_url):
        """Test body size limit enforcement."""
        try:
            # Create a large payload (>256KB)
            large_payload = {
                "version": "1.0",
                "message_id": str(uuid.uuid4()),
                "ts": datetime.now(timezone.utc).isoformat(),
                "type": "message",
                "sender": {"agent_id": "test"},
                "recipient": {"agent_id": "test"},
                "payload": {"data": "x" * (256 * 1024 + 1)},  # >256KB
                "ttl_ms": 30000
            }
            
            response = requests.post(
                f"{base_url}/api/v1/coordination",
                json=large_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            assert response.status_code == 413  # Payload Too Large
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running")
    
    def test_envelope_validation(self, base_url):
        """Test envelope schema validation."""
        try:
            # Test invalid envelope (missing required fields)
            invalid_envelope = {
                "version": "1.0",
                "message_id": "invalid-uuid",
                # Missing required fields
            }
            
            headers = {
                "Content-Type": "application/json",
                "X-Brikk-Key": "test-key",
                "X-Brikk-Timestamp": str(int(time.time())),
                "X-Brikk-Signature": "test-signature"
            }
            
            response = requests.post(
                f"{base_url}/api/v1/coordination",
                json=invalid_envelope,
                headers=headers,
                timeout=5
            )
            
            # Should fail validation (422 or 400)
            assert response.status_code in [400, 422]
            
            data = response.json()
            assert "request_id" in data
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running")
    
    def test_authentication_when_enabled(self, base_url, valid_envelope):
        """Test authentication behavior when per-org keys are enabled."""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Brikk-Key": "test-key",
                "X-Brikk-Timestamp": str(int(time.time())),
                "X-Brikk-Signature": "invalid-signature"
            }
            
            response = requests.post(
                f"{base_url}/api/v1/coordination",
                json=valid_envelope,
                headers=headers,
                timeout=5
            )
            
            # Behavior depends on BRIKK_FEATURE_PER_ORG_KEYS flag
            per_org_keys = os.getenv("BRIKK_FEATURE_PER_ORG_KEYS", "false").lower()
            
            if per_org_keys == "true":
                # Should fail authentication
                assert response.status_code == 401
            else:
                # Should proceed to envelope validation
                assert response.status_code in [400, 422]
            
            data = response.json()
            assert "request_id" in data
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running")
    
    def test_rate_limiting_when_enabled(self, base_url, valid_envelope):
        """Test rate limiting behavior when enabled."""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Brikk-Key": "test-key",
                "X-Brikk-Timestamp": str(int(time.time())),
                "X-Brikk-Signature": "test-signature"
            }
            
            # Make multiple requests quickly
            responses = []
            for _ in range(3):
                response = requests.post(
                    f"{base_url}/api/v1/coordination",
                    json=valid_envelope,
                    headers=headers,
                    timeout=5
                )
                responses.append(response)
            
            # Check if rate limiting headers are present
            for response in responses:
                rate_limit_enabled = os.getenv("BRIKK_RLIMIT_ENABLED", "false").lower()
                
                if rate_limit_enabled == "true":
                    # Should have rate limit headers
                    assert "X-RateLimit-Limit" in response.headers
                    assert "X-RateLimit-Remaining" in response.headers
                    assert "X-RateLimit-Reset" in response.headers
                
                # All should have request ID
                assert "X-Request-ID" in response.headers
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running")
    
    def test_idempotency_when_enabled(self, base_url, valid_envelope):
        """Test idempotency behavior when enabled."""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Brikk-Key": "test-key",
                "X-Brikk-Timestamp": str(int(time.time())),
                "X-Brikk-Signature": "test-signature",
                "Idempotency-Key": "test-idempotency-key"
            }
            
            # Make the same request twice
            response1 = requests.post(
                f"{base_url}/api/v1/coordination",
                json=valid_envelope,
                headers=headers,
                timeout=5
            )
            
            response2 = requests.post(
                f"{base_url}/api/v1/coordination",
                json=valid_envelope,
                headers=headers,
                timeout=5
            )
            
            # Both should have request IDs
            assert "X-Request-ID" in response1.headers
            assert "X-Request-ID" in response2.headers
            
            # Behavior depends on feature flags and authentication
            idem_enabled = os.getenv("BRIKK_IDEM_ENABLED", "true").lower()
            
            if idem_enabled == "true":
                # If idempotency is working, responses should be similar
                # (exact behavior depends on auth and other factors)
                assert response1.status_code == response2.status_code
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running")


class TestCoordinationAPIErrorHandling:
    """Test coordination API error handling."""
    
    @pytest.fixture(scope="class")
    def base_url(self):
        """Base URL for local Flask app."""
        return "http://localhost:8000"
    
    def test_malformed_json(self, base_url):
        """Test handling of malformed JSON."""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Brikk-Key": "test-key",
                "X-Brikk-Timestamp": str(int(time.time())),
                "X-Brikk-Signature": "test-signature"
            }
            
            response = requests.post(
                f"{base_url}/api/v1/coordination",
                data="invalid json {",
                headers=headers,
                timeout=5
            )
            
            assert response.status_code == 400
            
            data = response.json()
            assert "request_id" in data
            assert "code" in data
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running")
    
    def test_empty_body(self, base_url):
        """Test handling of empty request body."""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Brikk-Key": "test-key",
                "X-Brikk-Timestamp": str(int(time.time())),
                "X-Brikk-Signature": "test-signature"
            }
            
            response = requests.post(
                f"{base_url}/api/v1/coordination",
                data="",
                headers=headers,
                timeout=5
            )
            
            assert response.status_code == 400
            
            data = response.json()
            assert "request_id" in data
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running")
    
    def test_error_response_format(self, base_url):
        """Test that error responses follow consistent format."""
        try:
            # Make a request that will definitely fail
            response = requests.post(f"{base_url}/api/v1/coordination", timeout=5)
            
            # Should be an error
            assert response.status_code >= 400
            
            # Should be JSON
            assert response.headers["content-type"] == "application/json"
            
            data = response.json()
            
            # Should have consistent error format
            required_fields = {"code", "message", "request_id"}
            assert all(field in data for field in required_fields)
            
            # Request ID should be valid UUID
            uuid.UUID(data["request_id"])
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
