import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from flask.testing import FlaskClient

from src.factory import create_app
from src.database import db
from src.models.user import User
from src.models.org import Organization
from src.services.jwt_service import JWTService
from src.services.webhook_service import WebhookService
from src.services.api_connectors import get_connector, SlackConnector

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

@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    return app.test_client()

@pytest.fixture()
def auth_headers(app: Flask) -> dict:
    with app.app_context():
        org = Organization(name="Test Org", slug="test-org")
        db.session.add(org)
        db.session.commit()

        user = User(email="test@example.com", username="testuser", org_id=org.id)
        user.set_password("password")
        db.session.add(user)
        db.session.commit()

        jwt_service = JWTService(app.config["JWT_SECRET_KEY"])
        token = jwt_service.create_token(identity=user.id, claims={"organization_id": org.id})
        return {"Authorization": f"Bearer {token}", "organization_id": org.id}

# --- Webhook Tests ---

def test_create_webhook(client: FlaskClient, auth_headers: dict):
    """Test creating a new webhook subscription"""
    webhook_data = {
        "url": "https://example.com/webhook",
        "secret": "supersecret",
        "events": ["agent.created", "coordination.completed"]
    }
    
    response = client.post("/api/v1/webhooks", json=webhook_data, headers=auth_headers)
    assert response.status_code == 201
    assert response.json["url"] == webhook_data["url"]

def test_get_webhooks(client: FlaskClient, auth_headers: dict):
    """Test getting all webhooks for an organization"""
    # First, create a webhook
    client.post("/api/v1/webhooks", json={
        "url": "https://example.com/webhook",
        "secret": "supersecret",
        "events": ["agent.created"]
    }, headers=auth_headers)
    
    response = client.get("/api/v1/webhooks", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json) == 1

def test_update_webhook(client: FlaskClient, auth_headers: dict):
    """Test updating a webhook"""
    create_response = client.post("/api/v1/webhooks", json={
        "url": "https://example.com/webhook",
        "secret": "supersecret",
        "events": ["agent.created"]
    }, headers=auth_headers)
    webhook_id = create_response.json["id"]
    
    update_data = {"is_active": False}
    response = client.put(f"/api/v1/webhooks/{webhook_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    
    get_response = client.get(f"/api/v1/webhooks/{webhook_id}", headers=auth_headers)
    assert get_response.json["is_active"] == False

def test_delete_webhook(client: FlaskClient, auth_headers: dict):
    """Test deleting a webhook"""
    create_response = client.post("/api/v1/webhooks", json={
        "url": "https://example.com/webhook",
        "secret": "supersecret",
        "events": ["agent.created"]
    }, headers=auth_headers)
    webhook_id = create_response.json["id"]
    
    response = client.delete(f"/api/v1/webhooks/{webhook_id}", headers=auth_headers)
    assert response.status_code == 200
    
    get_response = client.get(f"/api/v1/webhooks/{webhook_id}", headers=auth_headers)
    assert get_response.status_code == 404

@patch("requests.post")
def test_webhook_event_trigger(mock_post, app: Flask, auth_headers: dict):
    """Test triggering a webhook event"""
    mock_post.return_value.status_code = 200
    
    with app.app_context():
        db_session = db.session
        webhook_service = WebhookService(db_session)
        
        # Create a webhook
        webhook = webhook_service.create_webhook(
            organization_id=auth_headers["organization_id"],
            url="https://example.com/webhook",
            secret="secret",
            events=["test.event"]
        )
        
        # Trigger an event
        webhook_service.trigger_event(
            event_type="test.event",
            payload_data={"key": "value"},
            organization_id=auth_headers["organization_id"]
        )
        
        # Verify that requests.post was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args.kwargs["url"] == webhook.url
        assert "X-Brikk-Signature" in call_args.kwargs["headers"]

