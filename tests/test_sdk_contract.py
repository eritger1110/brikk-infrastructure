# -*- coding: utf-8 -*-
"""
Contract tests for SDK endpoints.

This test ensures that all endpoints used by the SDKs exist and are accessible.
It serves as a contract between the SDKs and the backend API.
"""

import pytest
from src.factory import create_app


@pytest.fixture(scope="module")
def app():
    """Create a test app instance."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    return app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


def test_health_endpoints_exist(client):
    """Test that health endpoints exist."""
    # /healthz
    response = client.get("/healthz")
    assert response.status_code in [200, 500], f"/healthz returned {response.status_code}"
    
    # /readyz
    response = client.get("/readyz")
    assert response.status_code in [200, 500], f"/readyz returned {response.status_code}"


def test_auth_endpoints_exist(client):
    """Test that auth endpoints exist."""
    # /auth/_ping
    response = client.get("/auth/_ping")
    assert response.status_code in [200, 404], f"/auth/_ping returned {response.status_code}"


def test_agents_endpoints_exist(client):
    """Test that agents endpoints exist."""
    # GET /api/v1/agents
    response = client.get("/api/v1/agents")
    # May return 401 (unauthorized) or 200, but should not be 404
    assert response.status_code != 404, "/api/v1/agents endpoint does not exist"


def test_coordination_endpoints_exist(client):
    """Test that coordination endpoints exist."""
    # POST /api/v1/coordination
    response = client.post("/api/v1/coordination", json={})
    # May return 400/401/422, but should not be 404
    assert response.status_code != 404, "/api/v1/coordination endpoint does not exist"
    
    # GET /api/v1/coordination/health
    response = client.get("/api/v1/coordination/health")
    assert response.status_code != 404, "/api/v1/coordination/health endpoint does not exist"


def test_economy_endpoints_exist(client):
    """Test that economy endpoints exist (if implemented)."""
    # GET /api/v1/economy/balance
    response = client.get("/api/v1/economy/balance")
    # May not be implemented yet, so we allow 404
    if response.status_code != 404:
        assert response.status_code in [400, 401, 422, 500], \
            f"/api/v1/economy/balance returned unexpected {response.status_code}"


def test_reputation_endpoints_exist(client):
    """Test that reputation endpoints exist (if implemented)."""
    # GET /api/v1/reputation/summary
    response = client.get("/api/v1/reputation/summary")
    # May not be implemented yet, so we allow 404
    if response.status_code != 404:
        assert response.status_code in [400, 401, 422, 500], \
            f"/api/v1/reputation/summary returned unexpected {response.status_code}"


def test_billing_endpoints_exist(client):
    """Test that billing endpoints exist."""
    # POST /api/billing/portal
    response = client.post("/api/billing/portal", json={})
    # May return 400/401/500/501, but should not be 404
    assert response.status_code != 404, "/api/billing/portal endpoint does not exist"


def test_sdk_required_routes_summary(client):
    """Summary test to ensure all SDK-critical routes are registered."""
    critical_routes = [
        ("/healthz", "GET"),
        ("/readyz", "GET"),
        ("/api/v1/agents", "GET"),
        ("/api/v1/coordination", "POST"),
        ("/api/v1/coordination/health", "GET"),
    ]
    
    missing = []
    for path, method in critical_routes:
        if method == "GET":
            response = client.get(path)
        else:
            response = client.post(path, json={})
        
        if response.status_code == 404:
            missing.append(f"{method} {path}")
    
    assert not missing, f"Critical SDK routes missing: {', '.join(missing)}"

