# -*- coding: utf-8 -*-
"""
Manus Agent Adapter

Adapter for communicating with Manus AI agent.
"""
import os
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

MANUS_API_URL = os.getenv("MANUS_API_URL", "")
MANUS_API_KEY = os.getenv("MANUS_API_KEY", "")


def invoke_manus(message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Invoke the Manus agent with a message.
    
    Args:
        message: The message to send to Manus
        context: Optional context object
    
    Returns:
        Response from Manus agent
    """
    if not MANUS_API_URL:
        logger.warning("MANUS_API_URL not configured, using mock response")
        return {
            "ok": True,
            "result": f"[Manus Mock] Received: {message}",
            "meta": {"mock": True}
        }
    
    payload = {
        "message": message,
        "context": context or {}
    }
    
    headers = {"Content-Type": "application/json"}
    if MANUS_API_KEY:
        headers["Authorization"] = f"Bearer {MANUS_API_KEY}"
    
    try:
        logger.info(
            "Invoking Manus agent",
            extra={
                "endpoint": MANUS_API_URL,
                "message_length": len(message)
            }
        )
        
        resp = requests.post(
            MANUS_API_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()
        
        result = resp.json()
        
        logger.info(
            "Manus agent responded",
            extra={
                "status_code": resp.status_code,
                "response_size": len(resp.text)
            }
        )
        
        return result
    
    except requests.exceptions.RequestException as e:
        logger.error(
            "Manus agent invocation failed",
            extra={"error": str(e)}
        )
        return {
            "ok": False,
            "error": f"Manus API error: {str(e)}"
        }

