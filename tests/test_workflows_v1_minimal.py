import pytest
from flask import Flask
from flask.testing import FlaskClient
from src.factory import create_app
from src.database import db
from src.models.user import User
from src.models.org import Organization
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

