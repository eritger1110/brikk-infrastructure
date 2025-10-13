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


class TestApiKeyRotation:
    """Test API key rotation functionality."""

    @pytest.fixture
    def test_org(self, app):
        """Create test organization."""
        with app.app_context():
            org = Organization(
                name="Test Organization",
                slug="test-org",
                description="Test organization for rotation tests"
            )
            db.session.add(org)
            db.session.commit()
            return org

    @pytest.fixture
    def test_agent(self, app, test_org):
        """Create test agent."""
        with app.app_context():
            agent = Agent(
                name="Test Agent for Rotation",
                organization_id=test_org.id
            )
            db.session.add(agent)
            db.session.commit()
            return agent

    def test_api_key_creation(self, app, test_org, test_agent):
        """Test API key creation with proper encryption."""
        with app.app_context():
            with patch.dict(os.environ, {"BRIKK_ENCRYPTION_KEY": "test_key_32_bytes_long_for_fernet"}):
                api_key, secret = ApiKey.create_api_key(
                    organization_id=test_org.id,
                    name="Test Key for Rotation",
                    agent_id=test_agent.id
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
            with patch.dict(os.environ, {"BRIKK_ENCRYPTION_KEY": "test_key_32_bytes_long_for_fernet"}):
                # Create initial API key
                api_key, original_secret = ApiKey.create_api_key(
                    organization_id=test_org.id,
                    name="Test Key for Rotation",
                    agent_id=test_agent.id
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

    def test_api_key_rotation_window(self, app, test_org, test_agent):
        """Test API key rotation with grace period for old keys."""
        with app.app_context():
            with patch.dict(os.environ, {"BRIKK_ENCRYPTION_KEY": "test_key_32_bytes_long_for_fernet"}):
                # Create API key
                api_key, original_secret = ApiKey.create_api_key(
                    organization_id=test_org.id,
                    name="Test Key for Rotation Window",
                    agent_id=test_agent.id
                )

                # Test HMAC with original secret
                body = b'{"message_id": "test_123", "data": "test"}'
                timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

                original_signature = HMACSecurityService.create_signature(
                    method="POST",
                    path="/api/v1/coordination",
                    timestamp=timestamp,
                    body=body,
                    secret=original_secret,
                    message_id="test_123"
                )

                # Verify original signature works
                is_valid = HMACSecurityService.verify_signature(
                    method="POST",
                    path="/api/v1/coordination",
                    timestamp=timestamp,
                    body=body,
                    secret=original_secret,
                    provided_signature=original_signature,
                    message_id="test_123"
                )
                assert is_valid

                # Rotate secret
                new_secret = api_key.rotate_secret()

                # Test HMAC with new secret
                new_signature = HMACSecurityService.create_signature(
                    method="POST",
                    path="/api/v1/coordination",
                    timestamp=timestamp,
                    body=body,
                    secret=new_secret,
                    message_id="test_123"
                )

                # Verify new signature works
                is_valid = HMACSecurityService.verify_signature(
                    method="POST",
                    path="/api/v1/coordination",
                    timestamp=timestamp,
                    body=body,
                    secret=new_secret,
                    provided_signature=new_signature,
                    message_id="test_123"
                )
                assert is_valid

                # Verify old signature no longer works with new secret
                is_valid = HMACSecurityService.verify_signature(
                    method="POST",
                    path="/api/v1/coordination",
                    timestamp=timestamp,
                    body=body,
                    secret=new_secret,
                    provided_signature=original_signature,
                    message_id="test_123"
                )
                assert not is_valid

    def test_api_key_disable(self, app, test_org, test_agent):
        """Test API key disabling."""
        with app.app_context():
            with patch.dict(os.environ, {"BRIKK_ENCRYPTION_KEY": "test_key_32_bytes_long_for_fernet"}):
                # Create API key
                api_key, secret = ApiKey.create_api_key(
                    organization_id=test_org.id,
                    name="Test Key for Disabling",
                    agent_id=test_agent.id
                )

                # Verify key is initially valid
                assert api_key.is_valid()
                assert api_key.status == "active"

                # Disable key
                api_key.disable()

                # Verify key is disabled
                assert not api_key.is_valid()
                assert api_key.status == "disabled"
                assert api_key.disabled_at is not None

    def test_api_key_expiration(self, app, test_org, test_agent):
        """Test API key expiration."""
        with app.app_context():
            with patch.dict(os.environ, {"BRIKK_ENCRYPTION_KEY": "test_key_32_bytes_long_for_fernet"}):
                # Create API key with short expiration
                api_key, secret = ApiKey.create_api_key(
                    organization_id=test_org.id,
                    name="Test Key for Expiration",
                    agent_id=test_agent.id,
                    expires_days=1
                )

                # Verify key is initially valid
                assert api_key.is_valid()

                # Manually set expiration to past
                api_key.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
                db.session.commit()

                # Verify key is now expired
                assert not api_key.is_valid()

    def test_api_key_usage_tracking(self, app, test_org, test_agent):
        """Test API key usage tracking."""
        with app.app_context():
            with patch.dict(os.environ, {"BRIKK_ENCRYPTION_KEY": "test_key_32_bytes_long_for_fernet"}):
                # Create API key
                api_key, secret = ApiKey.create_api_key(
                    organization_id=test_org.id,
                    name="Test Key for Usage Tracking",
                    agent_id=test_agent.id
                )

                # Initial usage should be zero
                assert api_key.total_requests == 0
                assert api_key.successful_requests == 0
                assert api_key.failed_requests == 0
                assert api_key.last_used_at is None

                # Update usage - successful request
                api_key.update_usage(success=True)

                assert api_key.total_requests == 1
                assert api_key.successful_requests == 1
                assert api_key.failed_requests == 0
                assert api_key.last_used_at is not None

                # Update usage - failed request
                api_key.update_usage(success=False)

                assert api_key.total_requests == 2
                assert api_key.successful_requests == 1
                assert api_key.failed_requests == 1


class TestAdminEndpoints:
    """Test admin endpoints for API key management."""

    @pytest.fixture
    def admin_headers(self):
        """Create admin authentication headers."""
        return {
            "Authorization": "Bearer test_admin_token",
            "Content-Type": "application/json"
        }

    def test_admin_health_endpoint(self, client):
        """Test admin health endpoint."""
        response = client.get("/internal/health")
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["service"] == "auth_admin"
        assert "admin_configured" in data

    def test_create_organization_success(self, client, admin_headers):
        """Test successful organization creation."""
        org_data = {
            "name": "Test Organization",
            "slug": "test-org",
            "description": "Test organization for admin tests",
            "contact_email": "admin@test-org.com",
            "contact_name": "Test Admin"
        }

        with patch.dict(os.environ, {"BRIKK_ADMIN_TOKEN": "test_admin_token"}):
            response = client.post("/internal/organizations",
                                 data=json.dumps(org_data),
                                 headers=admin_headers)

        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == org_data["name"]
        assert data["slug"] == org_data["slug"]
        assert "id" in data

    def test_create_organization_duplicate_slug(self, client, admin_headers):
        """Test organization creation with duplicate slug."""
        org_data = {
            "name": "Test Organization",
            "slug": "test-org",
            "description": "Test organization"
        }

        with patch.dict(os.environ, {"BRIKK_ADMIN_TOKEN": "test_admin_token"}):
            # Create first organization
            response1 = client.post("/internal/organizations",
                                  data=json.dumps(org_data),
                                  headers=admin_headers)
            assert response1.status_code == 201

            # Try to create duplicate
            response2 = client.post("/internal/organizations",
                                  data=json.dumps(org_data),
                                  headers=admin_headers)
            assert response2.status_code == 409

            data = response2.get_json()
            assert data["code"] == "organization_exists"

    def test_create_organization_no_admin_token(self, client):
        """Test organization creation without admin token."""
        org_data = {
            "name": "Test Organization",
            "slug": "test-org"
        }

        response = client.post("/internal/organizations",
                             data=json.dumps(org_data),
                             headers={"Content-Type": "application/json"})

        assert response.status_code == 401
        data = response.get_json()
        assert data["code"] == "admin_token_required"

    def test_create_organization_invalid_admin_token(self, client):
        """Test organization creation with invalid admin token."""
        org_data = {
            "name": "Test Organization",
            "slug": "test-org"
        }

        headers = {
            "Authorization": "Bearer invalid_token",
            "Content-Type": "application/json"
        }

        with patch.dict(os.environ, {"BRIKK_ADMIN_TOKEN": "correct_admin_token"}):
            response = client.post("/internal/organizations",
                                 data=json.dumps(org_data),
                                 headers=headers)

        assert response.status_code == 401
        data = response.get_json()
        assert data["code"] == "invalid_admin_token"

    def test_create_api_key_success(self, client, admin_headers):
        """Test successful API key creation."""
        # First create organization
        org_data = {
            "name": "Test Organization",
            "slug": "test-org",
            "description": "Test organization"
        }

        with patch.dict(os.environ, {
            "BRIKK_ADMIN_TOKEN": "test_admin_token",
            "BRIKK_ENCRYPTION_KEY": "test_key_32_bytes_long_for_fernet"
        }):
            org_response = client.post("/internal/organizations",
                                     data=json.dumps(org_data),
                                     headers=admin_headers)
            assert org_response.status_code == 201

            # Create API key
            key_data = {
                "organization_slug": "test-org",
                "name": "Test API Key",
                "description": "Test key for admin tests"
            }

            response = client.post("/internal/keys/create",
                                 data=json.dumps(key_data),
                                 headers=admin_headers)

        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == key_data["name"]

