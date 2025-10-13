# -*- coding: utf-8 -*-
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

    def test_compute_body_hash(self):
        """Test body hash computation."""
        body = b'{"message": "test"}'
        hash_result = HMACSecurityService.compute_body_hash(body)

        expected = hashlib.sha256(body).hexdigest()
        assert hash_result == expected


class TestAuthMiddleware:
    """Test authentication middleware functionality."""

    @pytest.fixture
    def auth_middleware(self):
        """Create auth middleware instance."""
        return AuthMiddleware()

    def test_is_feature_enabled_default_false(
            self, auth_middleware, app: Flask):
        """Test feature flag checking with default false."""
        with app.app_context():
            with patch.dict(os.environ, {}, clear=True):
                assert not auth_middleware.is_feature_enabled(
                    'TEST_FLAG', False)

    @patch('src.services.auth_middleware.request')
    def test_authenticate_request_feature_disabled(
            self, mock_request, app: Flask, auth_middleware):
        """Test authentication when per-org keys feature is disabled."""
        with app.test_request_context():
            with patch.dict(os.environ, {'BRIKK_FEATURE_PER_ORG_KEYS': 'false'}):
                success, error, status = auth_middleware.authenticate_request()
                assert success
                assert error is None
                assert status is None

    @patch('src.services.auth_middleware.request')
    def test_authenticate_request_missing_headers(
            self, mock_request, app: Flask, auth_middleware):
        """Test authentication with missing headers."""
        mock_request.headers = {}

        with app.test_request_context():
            with patch.dict(os.environ, {'BRIKK_FEATURE_PER_ORG_KEYS': 'true'}):
                success, error, status = auth_middleware.authenticate_request()
                assert not success
                assert error['code'] == 'protocol_error'
                assert status == 400
