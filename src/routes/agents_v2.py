# -*- coding: utf-8 -*-
"""
Agent Registry Routes (Phase 5-6)

Endpoints for registering, listing, and invoking AI agents.
"""
import logging
import uuid
import time
import requests
from flask import Blueprint, request, jsonify
from src.services.agent_registry_service import get_registry
from src.agents.manus_adapter import invoke_manus

logger = logging.getLogger(__name__)

bp = Blueprint("agents_v2", __name__, url_prefix="/agents")


@bp.route("/register", methods=["POST"])
def register_agent():
    """
    Register or update an agent.
    
    POST /agents/register
    {
        "id": "openai",
        "name": "OpenAI Relay",
        "type": "http",
        "endpoint": "https://api.getbrikk.com/agents/openai/chat",
        "expects": {"message": "string", "system": "string"},
        "returns": {"output": "string"}
    }
    """
    request_id = str(uuid.uuid4())
    data = request.get_json(force=True) or {}
    
    agent_id = data.get("id")
    if not agent_id:
        return jsonify({"ok": False, "error": "Missing 'id' field"}), 400
    
    registry = get_registry()
    agent = registry.register(agent_id, data)
    
    logger.info(
        "Agent registered via API",
        extra={
            "request_id": request_id,
            "agent_id": agent_id,
            "endpoint": agent.get("endpoint")
        }
    )
    
    return jsonify({"ok": True, "agent": agent}), 200


@bp.route("", methods=["GET"])
def list_agents():
    """
    List all registered agents.
    
    GET /agents
    """
    registry = get_registry()
    agents = registry.list_all()
    
    return jsonify({"ok": True, "agents": agents, "count": len(agents)}), 200


@bp.route("/<agent_id>/chat", methods=["POST"])
def chat_with_agent(agent_id: str):
    """
    Send a message to a specific agent.
    
    POST /agents/:id/chat
    {
        "message": "Hello, agent!"
    }
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    registry = get_registry()
    agent = registry.get(agent_id)
    
    if not agent:
        return jsonify({"ok": False, "error": f"Agent '{agent_id}' not found"}), 404
    
    data = request.get_json(force=True) or {}
    message = data.get("message", "")
    
    logger.info(
        "Agent chat request",
        extra={
            "request_id": request_id,
            "agent_id": agent_id,
            "message_length": len(message)
        }
    )
    
    try:
        # Route to the appropriate adapter
        if agent_id == "openai":
            # Call OpenAI relay
            endpoint = agent.get("endpoint")
            resp = requests.post(
                endpoint,
                json={"message": message},
                timeout=30
            )
            resp.raise_for_status()
            result = resp.json()
        
        elif agent_id == "manus":
            # Call Manus adapter
            result = invoke_manus(message, context={"request_id": request_id})
        
        else:
            # Generic HTTP agent
            endpoint = agent.get("endpoint")
            headers = {"Content-Type": "application/json"}
            
            # Add auth if configured
            auth_config = agent.get("auth", {})
            if auth_config.get("type") == "bearer":
                headers["Authorization"] = f"Bearer {auth_config.get('token')}"
            
            resp = requests.post(
                endpoint,
                json={"message": message},
                headers=headers,
                timeout=30
            )
            resp.raise_for_status()
            result = resp.json()
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "Agent chat response",
            extra={
                "request_id": request_id,
                "agent_id": agent_id,
                "latency_ms": latency_ms,
                "status": "success"
            }
        )
        
        return jsonify({
            "ok": True,
            "agent_id": agent_id,
            "result": result,
            "latency_ms": latency_ms
        }), 200
    
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.error(
            "Agent chat failed",
            extra={
                "request_id": request_id,
                "agent_id": agent_id,
                "latency_ms": latency_ms,
                "error": str(e),
                "status": "error"
            }
        )
        
        return jsonify({
            "ok": False,
            "error": str(e),
            "latency_ms": latency_ms
        }), 500




@bp.route("/bridge", methods=["POST"])
def bridge_agents():
    """
    Execute a multi-turn conversation between two agents.
    
    POST /agents/bridge
    {
        "from": "openai",
        "to": "manus",
        "message": "Hello from OpenAI",
        "maxTurns": 3
    }
    """
    from src.services.agent_bridge_service import get_bridge
    
    request_id = str(uuid.uuid4())
    data = request.get_json(force=True) or {}
    
    from_agent = data.get("from")
    to_agent = data.get("to")
    message = data.get("message", "")
    max_turns = data.get("maxTurns", 3)
    
    if not from_agent or not to_agent:
        return jsonify({
            "ok": False,
            "error": "Missing 'from' or 'to' field"
        }), 400
    
    if not message:
        return jsonify({
            "ok": False,
            "error": "Missing 'message' field"
        }), 400
    
    logger.info(
        "Bridge request received",
        extra={
            "request_id": request_id,
            "from": from_agent,
            "to": to_agent,
            "max_turns": max_turns
        }
    )
    
    bridge = get_bridge()
    result = bridge.bridge(
        from_agent=from_agent,
        to_agent=to_agent,
        message=message,
        max_turns=max_turns,
        request_id=request_id
    )
    
    if result.get("ok"):
        return jsonify(result), 200
    else:
        return jsonify(result), 500

