'''
Test suite for request guards middleware.

Tests:
- Content-Type validation (415 for wrong type)
- Body size limits (413 for >256KB)
- Required headers validation (400 for missing headers)
- Security headers presence on success and error responses
'''

import json
import pytest
from flask import Flask, jsonify, Blueprint

from src.services.request_guards import (
    request_guards,
    apply_request_guards_to_blueprint,
    MAX_BODY_SIZE
)
from src.services.security_headers import apply_security_headers_to_blueprint


@pytest.fixture
def test_blueprint():
    "Create test blueprint with middleware applied."
    bp = Blueprint('test', __name__)
    
    @bp.route('/test', methods=['POST'])
    def test_endpoint():
        return jsonify({"status": "success"}), 200
    
    # Apply middleware
    apply_request_guards_to_blueprint(bp)
    apply_security_headers_to_blueprint(bp)
    
    return bp


@pytest.fixture
def client(app, test_blueprint):
    "Create test client with blueprint registered."
    app.register_blueprint(test_blueprint)
    return app.test_client()


class TestContentTypeValidation:
    "Test Content-Type header validation."
    
    def test_valid_content_type(self, client):
        "Test that application/json content type is accepted."
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'application/json',
                'X-Brikk-Key': 'test-key',
                'X-Brikk-Timestamp': '1234567890',
                'X-Brikk-Signature': 'test-signature'
            },
            json={"test": "data"}
        )
        assert response.status_code == 200
    
    def test_content_type_with_charset(self, client):
        "Test that application/json with charset is accepted."
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'application/json; charset=utf-8',
                'X-Brikk-Key': 'test-key',
                'X-Brikk-Timestamp': '1234567890',
                'X-Brikk-Signature': 'test-signature'
            },
            json={"test": "data"}
        )
        assert response.status_code == 200
    
    def test_wrong_content_type_text_plain(self, client):
        "Test that text/plain content type is rejected with 415."
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'text/plain',
                'X-Brikk-Key': 'test-key',
                'X-Brikk-Timestamp': '1234567890',
                'X-Brikk-Signature': 'test-signature'
            },
            data="plain text data"
        )
        assert response.status_code == 415
        data = response.get_json()
        assert data['code'] == 'protocol_error'
        assert 'Content-Type must be application/json' in data['message']
        assert 'request_id' in data
    
    def test_wrong_content_type_form_data(self, client):
        "Test that form data content type is rejected with 415."
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Brikk-Key': 'test-key',
                'X-Brikk-Timestamp': '1234567890',
                'X-Brikk-Signature': 'test-signature'
            },
            data="key=value"
        )
        assert response.status_code == 415
        data = response.get_json()
        assert data['code'] == 'protocol_error'
    
    def test_missing_content_type(self, client):
        "Test that missing Content-Type header is rejected with 415."
        response = client.post(
            '/test',
            headers={
                'X-Brikk-Key': 'test-key',
                'X-Brikk-Timestamp': '1234567890',
                'X-Brikk-Signature': 'test-signature'
            },
            data='{"test": "data"}'
        )
        assert response.status_code == 415


class TestBodySizeValidation:
    "Test request body size limits."
    
    def test_small_body_accepted(self, client):
        "Test that small request body is accepted."
        small_data = {"data": "x" * 1000}  # 1KB
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'application/json',
                'X-Brikk-Key': 'test-key',
                'X-Brikk-Timestamp': '1234567890',
                'X-Brikk-Signature': 'test-signature'
            },
            json=small_data
        )
        assert response.status_code == 200
    
    def test_max_size_body_accepted(self, client):
        "Test that body at max size limit is accepted."
        # Create data close to but under the limit
        max_data = {"data": "x" * (MAX_BODY_SIZE - 1000)}
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'application/json',
                'X-Brikk-Key': 'test-key',
                'X-Brikk-Timestamp': '1234567890',
                'X-Brikk-Signature': 'test-signature'
            },
            json=max_data
        )
        assert response.status_code == 200
    
    def test_oversized_body_rejected(self, client):
        "Test that oversized request body is rejected with 413."
        # Create data larger than the limit
        large_data = "x" * (MAX_BODY_SIZE + 1000)
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'application/json',
                'Content-Length': str(len(large_data)),
                'X-Brikk-Key': 'test-key',
                'X-Brikk-Timestamp': '1234567890',
                'X-Brikk-Signature': 'test-signature'
            },
            data=large_data
        )
        assert response.status_code == 413
        data = response.get_json()
        assert data['code'] == 'protocol_error'
        assert 'Request body too large' in data['message']
        assert f'{MAX_BODY_SIZE} bytes' in data['message']
    
    def test_invalid_content_length_header(self, client):
        "Test that invalid Content-Length header is rejected with 400."
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'application/json',
                'Content-Length': 'invalid',
                'X-Brikk-Key': 'test-key',
                'X-Brikk-Timestamp': '1234567890',
                'X-Brikk-Signature': 'test-signature'
            },
            json={"test": "data"}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 'protocol_error'
        assert 'Invalid Content-Length header' in data['message']


class TestRequiredHeaders:
    "Test required Brikk headers validation."
    
    def test_all_headers_present(self, client):
        "Test that request with all required headers is accepted."
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'application/json',
                'X-Brikk-Key': 'test-key',
                'X-Brikk-Timestamp': '1234567890',
                'X-Brikk-Signature': 'test-signature'
            },
            json={"test": "data"}
        )
        assert response.status_code == 200
    
    def test_missing_brikk_key(self, client):
        "Test that missing X-Brikk-Key header is rejected with 400."
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'application/json',
                'X-Brikk-Timestamp': '1234567890',
                'X-Brikk-Signature': 'test-signature'
            },
            json={"test": "data"}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 'protocol_error'
        assert 'Missing required headers' in data['message']
        assert 'X-Brikk-Key' in data['message']
    
    def test_missing_brikk_timestamp(self, client):
        "Test that missing X-Brikk-Timestamp header is rejected with 400."
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'application/json',
                'X-Brikk-Key': 'test-key',
                'X-Brikk-Signature': 'test-signature'
            },
            json={"test": "data"}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 'protocol_error'
        assert 'X-Brikk-Timestamp' in data['message']
    
    def test_missing_brikk_signature(self, client):
        "Test that missing X-Brikk-Signature header is rejected with 400."
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'application/json',
                'X-Brikk-Key': 'test-key',
                'X-Brikk-Timestamp': '1234567890'
            },
            json={"test": "data"}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 'protocol_error'
        assert 'X-Brikk-Signature' in data['message']
    
    def test_missing_multiple_headers(self, client):
        "Test that missing multiple headers are all reported."
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'application/json',
                'X-Brikk-Key': 'test-key'
            },
            json={"test": "data"}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['code'] == 'protocol_error'
        assert 'X-Brikk-Timestamp' in data['message']
        assert 'X-Brikk-Signature' in data['message']
    
    def test_empty_header_values(self, client):
        "Test that empty header values are treated as missing."
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'application/json',
                'X-Brikk-Key': '',
                'X-Brikk-Timestamp': '1234567890',
                'X-Brikk-Signature': 'test-signature'
            },
            json={"test": "data"}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'X-Brikk-Key' in data['message']


class TestSecurityHeaders:
    "Test that security headers are added to responses."
    
    def test_security_headers_on_success(self, client):
        "Test that security headers are added to successful responses."
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'application/json',
                'X-Brikk-Key': 'test-key',
                'X-Brikk-Timestamp': '1234567890',
                'X-Brikk-Signature': 'test-signature'
            },
            json={"test": "data"}
        )
        assert response.status_code == 200
        
        # Check security headers
        assert response.headers.get('Strict-Transport-Security') == 'max-age=31536000; includeSubDomains; preload'
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('Referrer-Policy') == 'no-referrer'
    
    def test_security_headers_on_error(self, client):
        "Test that security headers are added to error responses."
        response = client.post(
            '/test',
            headers={
                'Content-Type': 'text/plain'  # Wrong content type
            },
            data="test data"
        )
        assert response.status_code == 415
        
        # Check security headers are present even on error
        assert response.headers.get('Strict-Transport-Security') == 'max-age=31536000; includeSubDomains; preload'
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('Referrer-Policy') == 'no-referrer'


class TestNonPostRequests:
    "Test that middleware only applies to POST requests."
    
    def test_get_request_bypasses_validation(self, app):
        "Test that GET requests bypass request guards."
        bp = Blueprint('test_get', __name__)
        
        @bp.route('/test-get', methods=['GET'])
        def test_get_endpoint():
            return jsonify({"status": "success"}), 200
        
        apply_request_guards_to_blueprint(bp)
        apply_security_headers_to_blueprint(bp)
        
        app.register_blueprint(bp)
        client = app.test_client()
        
        # GET request without any Brikk headers should succeed
        response = client.get('/test-get')
        assert response.status_code == 200
        
        # Security headers should still be present
        assert response.headers.get('Strict-Transport-Security') is not None

