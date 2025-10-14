# -*- coding: utf-8 -*-
"""Smoke tests for the Brikk SDK."""

import os
import pytest
from unittest.mock import Mock, patch

from brikk import BrikkClient, AuthError


@pytest.fixture
def client():
    """Create a test client."""
    return BrikkClient(
        base_url=os.getenv("BRIKK_BASE_URL", "http://localhost:8000"),
        api_key=os.getenv("BRIKK_API_KEY", "test-key"),
        signing_secret=os.getenv("BRIKK_SIGNING_SECRET", "test-secret"),
    )


def test_client_initialization():
    """Test that client can be initialized."""
    client = BrikkClient(base_url="http://localhost:8000", api_key="test")
    assert client.base_url == "http://localhost:8000"
    assert client.api_key == "test"


def test_client_from_env():
    """Test client initialization from environment variables."""
    with patch.dict(os.environ, {
        "BRIKK_BASE_URL": "https://api.example.com",
        "BRIKK_API_KEY": "env-key",
    }):
        client = BrikkClient()
        assert client.base_url == "https://api.example.com"
        assert client.api_key == "env-key"


def test_health_ping_real(client):
    """Test health ping against real endpoint (if available)."""
    try:
        result = client.health.ping()
        assert "status" in result
        print(f"Health check passed: {result}")
    except Exception as e:
        pytest.skip(f"Health endpoint not available: {e}")


def test_health_ping_mock():
    """Test health ping with mocked response."""
    client = BrikkClient(base_url="http://localhost:8000", api_key="test")
    
    with patch.object(client._http, "get", return_value={"status": "ok"}):
        result = client.health.ping()
        assert result == {"status": "ok"}


def test_agents_list_mock():
    """Test agents list with mocked response."""
    client = BrikkClient(base_url="http://localhost:8000", api_key="test")
    
    mock_agents = [
        {"id": "agent_1", "name": "Agent 1", "org_id": "org_123"},
        {"id": "agent_2", "name": "Agent 2", "org_id": "org_123"},
    ]
    
    with patch.object(client._http, "get", return_value={"agents": mock_agents}):
        agents = client.agents.list(org_id="org_123")
        assert len(agents) == 2
        assert agents[0]["name"] == "Agent 1"


def test_economy_balance_mock():
    """Test economy balance with mocked response."""
    client = BrikkClient(base_url="http://localhost:8000", api_key="test")
    
    with patch.object(client._http, "get", return_value={"balance": 1000}):
        balance = client.economy.get_balance("org_123")
        assert balance == 1000


def test_reputation_summary_mock():
    """Test reputation summary with mocked response."""
    client = BrikkClient(base_url="http://localhost:8000", api_key="test")
    
    mock_summary = {
        "average_score": 4.5,
        "total_agents": 10,
        "total_interactions": 500,
    }
    
    with patch.object(client._http, "get", return_value=mock_summary):
        summary = client.reputation.get_summary("org_123")
        assert summary["average_score"] == 4.5
        assert summary["total_agents"] == 10


def test_coordination_message_mock():
    """Test coordination message sending with mocked response."""
    client = BrikkClient(
        base_url="http://localhost:8000",
        api_key="test-key",
        signing_secret="test-secret",
    )
    
    mock_receipt = {
        "message_id": "msg_123",
        "status": "delivered",
        "timestamp": "2025-10-14T00:00:00Z",
    }
    
    with patch.object(client._http, "post", return_value=mock_receipt):
        receipt = client.coordination.send_message(
            sender_id="agent_1",
            recipient_id="agent_2",
            payload={"test": "data"},
        )
        assert receipt["status"] == "delivered"


def test_error_handling():
    """Test that errors are raised correctly."""
    client = BrikkClient(base_url="http://localhost:8000", api_key="test")
    
    with patch.object(client._http, "get", side_effect=AuthError("Unauthorized", 401)):
        with pytest.raises(AuthError) as exc_info:
            client.health.ping()
        assert "Unauthorized" in str(exc_info.value)

