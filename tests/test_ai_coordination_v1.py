# tests/test_ai_coordination_v1.py

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from src.factory import create_app
from src.database import db
from src.models.agent import Agent
from src.models.workflow import Workflow
from src.models.workflow_step import WorkflowStep

@pytest.fixture
def mock_ai_coordination_service():
    with patch("src.routes.ai_coordination.ai_coordination_service") as mock_service:
        yield mock_service

def test_intelligent_route_success(client, mock_ai_coordination_service):
    mock_ai_coordination_service.intelligent_route.return_value = {
        "message": "Workflow intelligently routed to agent Test Agent",
        "agent_id": 1,
        "workflow_execution_id": 123
    }

    response = client.post("/api/v1/ai/route", json={
        "workflow_id": 1,
        "initial_data": {"key": "value"}
    })

    assert response.status_code == 200
    assert response.json["message"] == "Workflow intelligently routed to agent Test Agent"
    mock_ai_coordination_service.intelligent_route.assert_called_once_with(1, {"key": "value"})

def test_intelligent_route_missing_parameters(client):
    response = client.post("/api/v1/ai/route", json={})
    assert response.status_code == 400
    assert "workflow_id and initial_data are required" in response.json["error"]

def test_intelligent_route_not_found(client, mock_ai_coordination_service):
    mock_ai_coordination_service.intelligent_route.side_effect = ValueError("Workflow not found")
    response = client.post("/api/v1/ai/route", json={
        "workflow_id": 999,
        "initial_data": {"key": "value"}
    })
    assert response.status_code == 404
    assert "Workflow not found" in response.json["error"]

def test_optimize_coordination_strategy_success(client, mock_ai_coordination_service):
    mock_ai_coordination_service.optimize_coordination_strategy.return_value = {
        "message": "Coordination strategy for workflow 1 optimized successfully.",
        "optimized_step_order": ["Step 2", "Step 1"]
    }

    response = client.post("/api/v1/ai/optimize", json={"workflow_id": 1})

    assert response.status_code == 200
    assert "optimized successfully" in response.json["message"]
    mock_ai_coordination_service.optimize_coordination_strategy.assert_called_once_with(1)

def test_optimize_coordination_strategy_missing_parameters(client):
    response = client.post("//api/v1/ai/optimize", json={})
    assert response.status_code == 400
    assert "workflow_id is required" in response.json["error"]

def test_optimize_coordination_strategy_not_found(client, mock_ai_coordination_service):
    mock_ai_coordination_service.optimize_coordination_strategy.side_effect = ValueError("Workflow not found")
    response = client.post("/api/v1/ai/optimize", json={"workflow_id": 999})
    assert response.status_code == 404
    assert "Workflow not found" in response.json["error"]

