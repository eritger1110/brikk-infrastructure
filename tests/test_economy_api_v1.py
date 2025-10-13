# -*- coding: utf-8 -*-
"""
Tests for the Economy API Layer (PR B)
"""

import pytest
from flask import Flask
from flask.testing import FlaskClient

from src.factory import create_app
from src.database import db


@pytest.fixture
def app() -> Flask:
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


def test_get_balance(client: FlaskClient):
    """Test retrieving the credit balance for an organization."""
    # This test requires a valid JWT token with an org_id
    # For now, we will mock the authentication
    headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTY3OTg1NjAwMCwianRpIjoiZGV2LWp3dC1pZCIsIm5iZiI6MTY3OTg1NjAwMCwiZXhwIjoxNjc5ODU5NjAwLCJzdWIiOnsiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwib3JnX2lkIjoiZGV2LW9yZy1pZCJ9fQ.mock_signature"}
    response = client.get("/api/v1/billing/balance", headers=headers)
    assert response.status_code == 200
    assert response.json == {"credits": 0}
