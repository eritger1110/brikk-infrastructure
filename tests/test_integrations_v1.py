import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from flask.testing import FlaskClient

from src.main import create_app, db
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

        user = User(email="test@example.com", password="password", organization_id=org.id)
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

# --- API Connector Tests ---

def test_get_connector_factory():
    """Test the API connector factory"""
    # Test Slack connector
    slack_config = {"token": "test_token"}
    slack_connector = get_connector("slack", slack_config)
    assert isinstance(slack_connector, SlackConnector)
    
    # Test unknown connector
    unknown_connector = get_connector("unknown", {})
    assert unknown_connector is None
    
    # Test missing config
    with pytest.raises(ValueError):
        get_connector("jira", {})

@patch("requests.Session.request")
def test_api_connector_base(mock_request):
    """Test the base ApiConnector class"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}
    mock_request.return_value = mock_response
    
    connector = get_connector("slack", {"token": "test_token"})
    
    # Test GET request
    connector.get("users.list")
    mock_request.assert_called_with("GET", "https://slack.com/api/users.list", params=None)
    
    # Test POST request
    connector.post("chat.postMessage", json_data={"channel": "C123", "text": "Hello"})
    mock_request.assert_called_with("POST", "https://slack.com/api/chat.postMessage", data=None, json={"channel": "C123", "text": "Hello"})

@patch("src.services.api_connectors.SlackConnector.post")
def test_slack_connector(mock_post):
    """Test the SlackConnector"""
    mock_post.return_value.json.return_value = {"ok": True}
    
    slack_connector = get_connector("slack", {"token": "test_token"})
    response = slack_connector.post_message("C12345", "Hello, world!")
    
    assert response["ok"] == True
    mock_post.assert_called_once_with("chat.postMessage", json_data={
        "channel": "C12345",
        "text": "Hello, world!",
        "attachments": []
    })

@patch("src.services.api_connectors.JiraConnector.post")
def test_jira_connector(mock_post):
    """Test the JiraConnector"""
    mock_post.return_value.json.return_value = {"id": "10001", "key": "PROJ-123"}
    
    jira_connector = get_connector("jira", {
        "base_url": "https://my-jira.atlassian.net",
        "username": "user@example.com",
        "api_token": "token"
    })
    
    response = jira_connector.create_issue("PROJ", "Test Issue", "This is a test.")
    
    assert response["key"] == "PROJ-123"
    mock_post.assert_called_once()

@patch("src.services.api_connectors.GitHubConnector.get")
def test_github_connector(mock_get):
    """Test the GitHubConnector"""
    mock_get.return_value.json.return_value = [{"name": "repo1"}, {"name": "repo2"}]
    
    github_connector = get_connector("github", {"token": "gh_token"})
    repos = github_connector.get_user_repos("testuser")
    
    assert len(repos) == 2
    assert repos[0]["name"] == "repo1"
    mock_get.assert_called_once_with("users/testuser/repos")

