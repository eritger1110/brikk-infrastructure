import pytest
from flask import Flask
from flask.testing import FlaskClient
from datetime import datetime, timezone, timedelta

from src.factory import create_app
from src.database import db
from src.models.user import User
from src.models.org import Organization
from src.models.agent import Agent
from src.models.discovery import AgentService
from src.services.jwt_service import JWTService
from src.services.discovery_service import DiscoveryService

@pytest.fixture()
def auth_headers(app: Flask) -> dict:
    with app.app_context():
        org = Organization(name="Test Org", slug="test-org")
        db.session.add(org)
        db.session.commit()

        agent = Agent(name="Test Agent", language="en", organization_id=org.id)
        db.session.add(agent)
        db.session.commit()

        jwt_service = JWTService(app.config["JWT_SECRET_KEY"])
        token = jwt_service.create_token(identity=agent.id, claims={"organization_id": org.id, "agent_id": agent.id})
        return {"Authorization": f"Bearer {token}", "organization_id": org.id, "agent_id": agent.id}

def test_register_service(client: FlaskClient, auth_headers: dict):
    """Test registering a new agent service"""
    service_data = {
        "service_name": "test-service",
        "service_url": "http://localhost:8080/service",
        "capabilities": ["data_processing", "nlp"]
    }
    
    response = client.post("/api/v1/discovery/register", json=service_data, headers=auth_headers)
    assert response.status_code == 201
    assert response.json["name"] == "test-service"

def test_discover_services(client: FlaskClient, auth_headers: dict):
    """Test discovering available services"""
    # Register a service first
    client.post("/api/v1/discovery/register", json={
        "service_name": "test-service",
        "service_url": "http://localhost:8080/service",
        "capabilities": ["data_processing"]
    }, headers=auth_headers)
    
    # Discover all services
    response = client.get("/api/v1/discovery/discover", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]["name"] == "test-service"
    
    # Discover by capability
    response = client.get("/api/v1/discovery/discover?capability=data_processing", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json) == 1
    
    # Discover by non-existent capability
    response = client.get("/api/v1/discovery/discover?capability=non_existent", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json) == 0

def test_service_heartbeat(client: FlaskClient, auth_headers: dict):
    """Test sending a heartbeat to a service"""
    create_response = client.post("/api/v1/discovery/register", json={
        "service_name": "test-service",
        "service_url": "http://localhost:8080/service",
        "capabilities": []
    }, headers=auth_headers)
    service_id = create_response.json["id"]
    
    response = client.post(f"/api/v1/discovery/services/{service_id}/heartbeat", headers=auth_headers)
    assert response.status_code == 200
    assert response.json["message"] == "Heartbeat received"

def test_service_expiration(app: Flask, auth_headers: dict):
    """Test that expired services are not discovered"""
    with app.app_context():
        discovery_service = DiscoveryService(db.session)
        
        # Register a service with a short TTL (mocking)
        service = discovery_service.register_service(
            agent_id=auth_headers["agent_id"],
            service_name="expiring-service",
            service_url="http://localhost:8080/expiring",
            capabilities=[]
        )
        service.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()
        
        # Try to discover the service
        services = discovery_service.discover_services()
        assert len(services) == 0
        
        # Verify cleanup removes the service
        removed_count = discovery_service.remove_expired_services()
        assert removed_count == 1

def test_get_service_details(client: FlaskClient, auth_headers: dict):
    """Test getting details of a specific service"""
    create_response = client.post("/api/v1/discovery/register", json={
        "service_name": "detailed-service",
        "service_url": "http://localhost:8080/detailed",
        "capabilities": ["test"]
    }, headers=auth_headers)
    service_id = create_response.json["id"]
    
    response = client.get(f"/api/v1/discovery/services/{service_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json["name"] == "detailed-service"
    assert "agent" in response.json

