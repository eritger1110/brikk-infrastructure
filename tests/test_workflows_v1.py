import pytest
from flask import Flask
from flask.testing import FlaskClient
from src.database import db
from src.models.user import User
from src.models.org import Organization
from src.models.agent import Agent
from src.services.jwt_service import JWTService

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


def test_create_workflow(client: FlaskClient, auth_headers: dict):
    response = client.post("/api/v1/workflows", json={
        "name": "Test Workflow",
        "description": "A test workflow"
    }, headers=auth_headers)
    assert response.status_code == 201
    assert response.json["name"] == "Test Workflow"

def test_get_workflow(client: FlaskClient, auth_headers: dict):
    # First, create a workflow
    create_response = client.post("/api/v1/workflows", json={
        "name": "Test Workflow",
        "description": "A test workflow"
    }, headers=auth_headers)
    workflow_id = create_response.json["id"]

    # Then, get the workflow
    get_response = client.get(f"/api/v1/workflows/{workflow_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json["name"] == "Test Workflow"

def test_create_workflow_step(client: FlaskClient, auth_headers: dict):
    with client.application.app_context():
        # First, create a workflow
        create_workflow_response = client.post("/api/v1/workflows", json={
            "name": "Test Workflow",
            "description": "A test workflow"
        }, headers=auth_headers)
        workflow_id = create_workflow_response.json["id"]

        # Then, create an agent
        org_id = auth_headers["organization_id"]
        agent = Agent(name="Test Agent", language="python", organization_id=org_id)
        db.session.add(agent)
        db.session.commit()

        # Then, create a workflow step
        create_step_response = client.post(f"/api/v1/workflows/{workflow_id}/steps", json={
            "name": "Test Step",
            "description": "A test step",
            "agent_id": agent.id,
            "action": "test_action",
            "params": {"param1": "value1"},
            "order": 1
        }, headers=auth_headers)
        assert create_step_response.status_code == 201
        assert create_step_response.json["name"] == "Test Step"

def test_execute_workflow(client: FlaskClient, auth_headers: dict):
    # First, create a workflow
    create_response = client.post("/api/v1/workflows", json={
        "name": "Test Workflow",
        "description": "A test workflow"
    }, headers=auth_headers)
    workflow_id = create_response.json["id"]

    # Then, execute the workflow
    execute_response = client.post(f"/api/v1/workflows/{workflow_id}/execute", json={
        "context": {"input": "test_input"}
    }, headers=auth_headers)
    assert execute_response.status_code == 202
    assert execute_response.json["status"] == "running"

