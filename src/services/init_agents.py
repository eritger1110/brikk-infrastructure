# -*- coding: utf-8 -*-
"""
Agent Initialization

Auto-registers default agents on application startup.
"""
import logging
import os
from src.services.agent_registry_service import get_registry

logger = logging.getLogger(__name__)


def init_default_agents():
    """
    Register default agents (OpenAI and Manus) on startup.
    """
    registry = get_registry()
    
    # Register OpenAI relay agent
    openai_agent = {
        "id": "openai",
        "name": "OpenAI Relay",
        "type": "http",
        "endpoint": f"{os.getenv('BRIKK_BASE_URL', 'https://api.getbrikk.com')}/agents/openai/chat",
        "expects": {
            "message": "string",
            "system": "string (optional)"
        },
        "returns": {
            "ok": "boolean",
            "output": "string"
        },
        "metadata": {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "provider": "OpenAI"
        }
    }
    
    registry.register("openai", openai_agent)
    logger.info("Registered OpenAI agent")
    
    # Register Manus agent
    manus_url = os.getenv("MANUS_API_URL", "")
    manus_agent = {
        "id": "manus",
        "name": "Manus AI Agent",
        "type": "http",
        "endpoint": manus_url or "mock://manus",
        "expects": {
            "message": "string",
            "context": "object (optional)"
        },
        "returns": {
            "ok": "boolean",
            "result": "string",
            "meta": "object"
        },
        "metadata": {
            "provider": "Manus",
            "mock_mode": not bool(manus_url)
        }
    }
    
    if os.getenv("MANUS_API_KEY"):
        manus_agent["auth"] = {
            "type": "bearer",
            "token": os.getenv("MANUS_API_KEY")
        }
    
    registry.register("manus", manus_agent)
    logger.info(
        "Registered Manus agent",
        extra={"mock_mode": not bool(manus_url)}
    )
    
    logger.info(f"Initialized {len(registry.list_all())} default agents")

