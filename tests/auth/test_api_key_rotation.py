"""
Test suite for API key rotation and admin endpoint functionality.
"""
import pytest
import json
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from src.models.org import Organization
from src.models.agent import Agent
from src.models.api_key import ApiKey
from src.services.security_enhanced import HMACSecurityService
from src.database import db


@pytest.fixture(scope="module")
def app():
    """Create Flask app for testing."""
    from flask import Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope="module")
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def test_org(app):
    """Create test organization."""
    with app.app_context():
        org = Organization(
            name="Test Organization",
            slug="test-org",
            description="Test organization for rotation tests",
        )
        db.session.add(org)
        db.session.commit()
        yield org
        db.session.delete(org)
        db.session.commit()


@pytest.fixture(scope="function")
def test_agent(app, test_org):
    """Create test agent."""
    with app.app_context():
        agent = Agent(
            name="Test Agent for Rotation",
            language="en",
            organization_id=test_org.id,
        )
        db.session.add(agent)
        db.session.commit()
        yield agent
        db.session.delete(agent)
        db.session.commit()


class TestApiKeyRotation:
    """Test API key rotation functionality."""

    def test_api_key_creation(self, app, test_org, test_agent):
        """Test API key creation with proper encryption."""
        with app.app_context():
            with patch.dict(
                os.environ, {"BRIKK_ENCRYPTION_KEY": "test_key_32_bytes_long_for_fernet"}
            ):
                api_key, secret = ApiKey.create_api_key(
                    organization_id=test_org.id,
                    name="Test Key for Rotation",
                    agent_id=test_agent.id,
                )

                assert api_key.key_id.startswith("bk_")
                assert len(secret) >= 32  # Minimum secret length
                assert api_key.organization_id == test_org.id
                assert api_key.agent_id == test_agent.id
                assert api_key.is_valid()

                # Verify secret can be decrypted
                decrypted_secret = api_key.decrypt_secret()
                assert decrypted_secret == secret

    def test_api_key_rotation(self, app, test_org, test_agent):
        """Test API key secret rotation."""
        with app.app_context():
            with patch.dict(
                os.environ, {"BRIKK_ENCRYPTION_KEY": "test_key_32_bytes_long_for_fernet"}
            ):
                # Create initial API key
                api_key, original_secret = ApiKey.create_api_key(
                    organization_id=test_org.id,
                    name="Test Key for Rotation",
                    agent_id=test_agent.id,
                )

                original_key_id = api_key.key_id

                # Rotate secret
                new_secret = api_key.rotate_secret()

                # Verify rotation
                assert new_secret != original_secret
                assert len(new_secret) >= 32
                assert api_key.key_id == original_key_id  # Key ID should not change

                # Verify new secret can be decrypted
                decrypted_secret = api_key.decrypt_secret()
                assert decrypted_secret == new_secret

                # Verify old secret no longer works
                assert decrypted_secret != original_secret

