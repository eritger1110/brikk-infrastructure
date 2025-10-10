import os
import time
import hmac
import hashlib
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from flask import Flask
from cryptography.fernet import Fernet

from src.main import create_app
from src.models.api_key import ApiKey
from src.models.org import Organization
from src.database.db import db


@pytest.fixture(scope="module")
def app():
    """Create a test app instance."""
    # Generate a valid Fernet key for testing
    test_key = Fernet.generate_key().decode()
    os.environ["BRIKK_ENCRYPTION_KEY"] = test_key
    os.environ["BRIKK_ALLOW_UUID4"] = "true"

    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "RATELIMIT_STORAGE_URI": "memory://",
        "BRIKK_FEATURE_PER_ORG_KEYS": "true",
        "BRIKK_IDEM_ENABLED": "true",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def org_and_key(app):
    """Create a test organization and API key."""
    with app.app_context():
        org = Organization(name="Test Org", slug=f"test-org-{uuid.uuid4()}")
        db.session.add(org)
        db.session.commit()

        api_key, secret = ApiKey.create_api_key(
            organization_id=org.id,
            name="Test Key",
        )
        api_key.signing_secret = secret
        yield org, api_key
        db.session.delete(api_key)
        db.session.delete(org)
        db.session.commit()


def generate_signature(timestamp, body, secret):
    """Generate HMAC-SHA256 signature."""
    message = f"{timestamp}.{body}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def test_coordination_v1_success(client, org_and_key):
    """Test successful call to the v1 coordination endpoint."""
    org, api_key = org_and_key
    timestamp = str(int(time.time()))
    body = {
        "version": "1.0",
        "message_id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "type": "event",
        "sender": {"agent_id": "agent-1"},
        "recipient": {"agent_id": "agent-2"},
        "payload": {"foo": "bar"},
        "ttl_ms": 60000,
    }
    body_str = json.dumps(body)
    signature = generate_signature(timestamp, body_str, api_key.signing_secret)

    headers = {
        "Content-Type": "application/json",
        "X-Brikk-Key": api_key.key_id,
        "X-Brikk-Timestamp": timestamp,
        "X-Brikk-Signature": signature,
    }

    response = client.post("/api/v1/coordination", headers=headers, data=body_str)

    assert response.status_code == 202
    json_data = response.get_json()
    assert json_data["status"] == "accepted"
    assert json_data["echo"]["message_id"] == body["message_id"]


def test_coordination_v1_invalid_signature(client, org_and_key):
    """Test failed call with invalid signature."""
    org, api_key = org_and_key
    timestamp = str(int(time.time()))
    body = {
        "version": "1.0",
        "message_id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "type": "event",
        "sender": {"agent_id": "agent-1"},
        "recipient": {"agent_id": "agent-2"},
        "payload": {"foo": "bar"},
        "ttl_ms": 60000,
    }
    body_str = json.dumps(body)
    signature = "invalid-signature"

    headers = {
        "Content-Type": "application/json",
        "X-Brikk-Key": api_key.key_id,
        "X-Brikk-Timestamp": timestamp,
        "X-Brikk-Signature": signature,
    }

    response = client.post("/api/v1/coordination", headers=headers, data=body_str)

    assert response.status_code == 401
    json_data = response.get_json()
    assert json_data["code"] == "auth_error"


def test_coordination_v1_idempotency(client, org_and_key):
    """Test idempotency handling."""
    org, api_key = org_and_key
    timestamp = str(int(time.time()))
    body = {
        "version": "1.0",
        "message_id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "type": "event",
        "sender": {"agent_id": "agent-1"},
        "recipient": {"agent_id": "agent-2"},
        "payload": {"foo": "bar"},
        "ttl_ms": 60000,
    }
    body_str = json.dumps(body)
    signature = generate_signature(timestamp, body_str, api_key.signing_secret)
    idempotency_key = f"idem-key-{uuid.uuid4()}"

    headers = {
        "Content-Type": "application/json",
        "X-Brikk-Key": api_key.key_id,
        "X-Brikk-Timestamp": timestamp,
        "X-Brikk-Signature": signature,
        "Idempotency-Key": idempotency_key,
    }

    # First request should succeed
    response1 = client.post("/api/v1/coordination", headers=headers, data=body_str)
    assert response1.status_code == 202

    # Second request with same idempotency key should be a replay
    response2 = client.post("/api/v1/coordination", headers=headers, data=body_str)
    assert response2.status_code == 200  # Replay returns 200
    assert response2.get_json() == response1.get_json()

    # Third request with same idempotency key but different body should fail
    body2 = body.copy()
    body2["payload"] = {"foo": "baz"}
    body2_str = json.dumps(body2)
    signature2 = generate_signature(timestamp, body2_str, api_key.signing_secret)
    headers2 = headers.copy()
    headers2["X-Brikk-Signature"] = signature2
    response3 = client.post("/api/v1/coordination", headers=headers2, data=body2_str)
    assert response3.status_code == 409  # Conflict
    assert response3.get_json()["code"] == "idempotency_conflict"

