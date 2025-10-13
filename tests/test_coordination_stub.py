# -*- coding: utf-8 -*-

import json
import uuid
import pytest


@pytest.fixture
def valid_headers():
    """Valid headers for coordination requests."""
    return {
        'Content-Type': 'application/json',
        'X-Brikk-Key': 'test-key-123',
        'X-Brikk-Timestamp': '1696248600',
        'X-Brikk-Signature': 'test-signature-abc123'
    }


@pytest.fixture
def valid_envelope():
    """Valid envelope data for testing."""
    return {
        "message_id": str(uuid.uuid4()),
        "ts": "2023-10-02T14:30:00.123Z",
        "type": "command",
        "sender": {'agent_id': "test-sender-001"},
        "recipient": {'agent_id': "test-recipient-002"},
        "payload": {
            "action": "coordinate",
            "data": {'key': "value"}
        },
        "ttl_ms": 45000
    }


class TestCoordinationEndpoint:
    """Test the main coordination endpoint."""

    def test_valid_request_returns_202(
            self, client, valid_headers, valid_envelope):
        """Test that valid request returns 202 with echo."""
        response = client.post(
            '/api/v1/coordination',
            headers=valid_headers,
            json=valid_envelope
        )

        assert response.status_code == 202
        data = response.get_json()

        assert data['status'] == 'accepted'
        assert 'echo' in data
        assert data['echo']['message_id'] == valid_envelope['message_id']

    def test_minimal_valid_envelope(self, client, valid_headers):
        """Test that minimal valid envelope is accepted."""
        minimal_envelope = {
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            "type": "command",
            "sender": {'agent_id': "sender-001"},
            "recipient": {'agent_id': "recipient-002"},
            "payload": {'action': "test"}
        }

        response = client.post(
            '/api/v1/coordination',
            headers=valid_headers,
            json=minimal_envelope
        )

        assert response.status_code == 202
        data = response.get_json()
        assert data['echo']['message_id'] == minimal_envelope['message_id']

    def test_security_headers_present(
            self, client, valid_headers, valid_envelope):
        """Test that security headers are present in response."""
        response = client.post(
            '/api/v1/coordination',
            headers=valid_headers,
            json=valid_envelope
        )

        assert response.status_code == 202

        # Check security headers
        assert response.headers.get(
            'Strict-Transport-Security') == 'max-age=31536000; includeSubDomains; preload'
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('Referrer-Policy') == 'no-referrer'


class TestRequestGuardsIntegration:
    """Test request guards integration with coordination endpoint."""

    def test_missing_content_type_returns_415(self, client, valid_envelope):
        """Test that missing Content-Type returns 415."""
        headers = {
            'X-Brikk-Key': 'test-key',
            'X-Brikk-Timestamp': '1696248600',
            'X-Brikk-Signature': 'test-signature'
        }

        response = client.post(
            '/api/v1/coordination',
            headers=headers,
            data=json.dumps(valid_envelope)
        )

        assert response.status_code == 415
        data = response.get_json()
        assert data['code'] == 'protocol_error'
        assert 'Content-Type must be application/json' in data['message']

    def test_missing_brikk_headers_returns_400(self, client, valid_envelope):
        """Test that missing Brikk headers return 400."""
        headers = {'Content-Type': 'application/json'}

        response = client.post(
            '/api/v1/coordination',
            headers=headers,
            json=valid_envelope
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 'protocol_error'
        assert 'Missing required headers' in data['message']

    def test_oversized_body_returns_413(self, client, valid_headers):
        """Test that oversized request body returns 413."""
        # Create large payload
        large_payload = {'data': "x" * (256 * 1024 + 1000)}  # >256KB
        large_envelope = {
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            "type": "command",
            "sender": {'agent_id': "sender-001"},
            "recipient": {'agent_id': "recipient-002"},
            "payload": large_payload
        }

        response = client.post(
            '/api/v1/coordination',
            headers=valid_headers,
            json=large_envelope
        )

        assert response.status_code == 413
        data = response.get_json()
        assert data['code'] == 'protocol_error'
        assert 'Request body too large' in data['message']


class TestEnvelopeValidationIntegration:
    """Test envelope validation integration with coordination endpoint."""

    def test_invalid_envelope_returns_422(self, client, valid_headers):
        """Test that invalid envelope returns 422."""
        invalid_envelope = {
            "message_id": "not-a-uuid",  # Invalid UUID
            "ts": "2023-10-02T14:30:00Z",
            "type": "command",
            "sender": {'agent_id': "sender-001"},
            "recipient": {'agent_id': "recipient-002"},
            "payload": {'action': "test"}
        }

        response = client.post(
            '/api/v1/coordination',
            headers=valid_headers,
            json=invalid_envelope
        )

        assert response.status_code == 422
        data = response.get_json()
        assert data['code'] == 'validation_error'
        assert 'Envelope validation failed' in data['message']
        assert 'details' in data
        assert any('message_id' in str(detail) for detail in data['details'])

    def test_missing_required_fields_returns_422(self, client, valid_headers):
        """Test that missing required fields return 422."""
        incomplete_envelope = {
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            # Missing sender, recipient, payload, type
        }

        response = client.post(
            '/api/v1/coordination',
            headers=valid_headers,
            json=incomplete_envelope
        )

        assert response.status_code == 422
        data = response.get_json()
        assert data['code'] == 'validation_error'
        assert 'details' in data

        # Check that all missing fields are reported
        details_str = ' '.join(str(d) for d in data['details'])
        assert 'sender' in details_str
        assert 'recipient' in details_str
        assert 'payload' in details_str
        assert 'type' in details_str

    def test_extra_fields_returns_422(
            self, client, valid_headers, valid_envelope):
        """Test that extra fields in envelope return 422."""
        envelope_with_extra = valid_envelope.copy()
        envelope_with_extra['extra_field'] = 'not_allowed'

        response = client.post(
            '/api/v1/coordination',
            headers=valid_headers,
            json=envelope_with_extra
        )

        assert response.status_code == 422
        data = response.get_json()
        assert data['code'] == 'validation_error'
        assert any('extra_field' in str(detail) for detail in data['details'])

    def test_invalid_timestamp_returns_422(
            self, client, valid_headers, valid_envelope):
        """Test that invalid timestamp format returns 422."""
        envelope_with_bad_ts = valid_envelope.copy()
        envelope_with_bad_ts['ts'] = '2023-10-02 14:30:00'  # Missing T and Z

        response = client.post(
            '/api/v1/coordination',
            headers=valid_headers,
            json=envelope_with_bad_ts
        )

        assert response.status_code == 422
        data = response.get_json()
        assert data['code'] == 'validation_error'
        assert any('ts' in str(detail) for detail in data['details'])

    def test_ttl_out_of_range_returns_422(
            self, client, valid_headers, valid_envelope):
        """Test that TTL out of range returns 422."""
        envelope_with_bad_ttl = valid_envelope.copy()
        envelope_with_bad_ttl['ttl_ms'] = 200000  # > 120000 limit

        response = client.post(
            '/api/v1/coordination',
            headers=valid_headers,
            json=envelope_with_bad_ttl
        )

        assert response.status_code == 422
        data = response.get_json()
        assert data['code'] == 'validation_error'
        assert any('ttl_ms' in str(detail) for detail in data['details'])


class TestErrorHandling:
    """Test error handling in coordination endpoint."""

    def test_invalid_json_returns_400(self, client, valid_headers):
        """Test that invalid JSON returns 400."""
        response = client.post(
            '/api/v1/coordination',
            headers=valid_headers,
            data='{"invalid": json}'  # Invalid JSON
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 'protocol_error'
        assert 'valid JSON' in data['message']

    def test_empty_body_returns_400(self, client, valid_headers):
        """Test that empty request body returns 400."""
        response = client.post(
            '/api/v1/coordination',
            headers=valid_headers,
            data=''
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 'protocol_error'
        assert 'valid JSON' in data['message']

    def test_error_responses_have_request_id(self, client, valid_headers):
        """Test that error responses include request_id."""
        response = client.post(
            '/api/v1/coordination',
            headers=valid_headers,
            data='invalid json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'request_id' in data

    def test_error_responses_have_security_headers(
            self, client, valid_headers):
        """Test that error responses include security headers."""
        response = client.post(
            '/api/v1/coordination',
            headers={'Content-Type': 'text/plain'},  # Wrong content type
            data='test'
        )

        assert response.status_code == 415

        # Security headers should be present even on errors
        assert response.headers.get('Strict-Transport-Security') is not None
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('Referrer-Policy') == 'no-referrer'


class TestHealthCheckEndpoint:
    """Test the health check endpoint."""

    def test_health_check_returns_200(self, client):
        """Test that health check endpoint returns 200."""
        response = client.get('/api/v1/coordination/health')

        assert response.status_code == 200
        data = response.get_json()

        assert data['status'] == 'healthy'
        assert data['service'] == 'coordination-api'
        assert data['version'] == '1.0-stub'

    def test_health_check_has_security_headers(self, client):
        """Test that health check response includes security headers."""
        response = client.get('/api/v1/coordination/health')

        assert response.status_code == 200

        # Security headers should be present
        assert response.headers.get('Strict-Transport-Security') is not None
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('Referrer-Policy') == 'no-referrer'

    def test_health_check_no_validation(self, client):
        """Test that health check bypasses request validation."""
        # GET request without any Brikk headers should work
        response = client.get('/api/v1/coordination/health')
        assert response.status_code == 200


class TestMessageTypes:
    """Test different message types in envelopes."""

    def test_all_message_types_accepted(self, client, valid_headers):
        """Test that all valid message types are accepted."""
        message_types = ["event", "command", "result", "error"]

        for msg_type in message_types:
            envelope = {
                "message_id": str(uuid.uuid4()),
                "ts": "2023-10-02T14:30:00Z",
                "type": msg_type,
                "sender": {'agent_id': "sender-001"},
                "recipient": {'agent_id': "recipient-002"},
                'payload': {'action': "test", 'type': msg_type}}

            response = client.post(
                '/api/v1/coordination',
                headers=valid_headers,
                json=envelope
            )

            assert response.status_code == 202, f"Failed for message type: {msg_type}"
            data = response.get_json()
            assert data['echo']['message_id'] == envelope['message_id']
