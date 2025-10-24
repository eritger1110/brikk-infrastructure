# -*- coding: utf-8 -*-
"""
Agent Bridge Service

Orchestrates multi-turn conversations between AI agents.
"""
import logging
import uuid
import time
import requests
from typing import List, Dict, Any
from src.services.agent_registry_service import get_registry
from src.agents.manus_adapter import invoke_manus

logger = logging.getLogger(__name__)


class AgentBridgeService:
    """
    Manages multi-turn conversations between registered agents.
    """
    
    def __init__(self):
        self.registry = get_registry()
    
    def bridge(
        self,
        from_agent: str,
        to_agent: str,
        message: str,
        max_turns: int = 3,
        request_id: str = None
    ) -> Dict[str, Any]:
        """
        Execute a multi-turn conversation between two agents.
        
        Args:
            from_agent: ID of the initiating agent
            to_agent: ID of the receiving agent
            message: Initial message
            max_turns: Maximum number of turns (default 3)
            request_id: Optional request ID for tracking
        
        Returns:
            Dictionary containing transcript and metadata
        """
        if not request_id:
            request_id = str(uuid.uuid4())
        
        start_time = time.time()
        transcript = []
        current_message = message
        current_from = from_agent
        current_to = to_agent
        
        logger.info(
            "Agent bridge session started",
            extra={
                "request_id": request_id,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "max_turns": max_turns
            }
        )
        
        for turn in range(max_turns):
            turn_start = time.time()
            
            # Get the receiving agent
            agent = self.registry.get(current_to)
            if not agent:
                error_msg = f"Agent '{current_to}' not found"
                logger.error(
                    "Bridge error",
                    extra={
                        "request_id": request_id,
                        "turn": turn,
                        "error": error_msg
                    }
                )
                return {
                    "ok": False,
                    "error": error_msg,
                    "transcript": transcript
                }
            
            # Invoke the agent
            try:
                response = self._invoke_agent(
                    agent_id=current_to,
                    agent=agent,
                    message=current_message,
                    request_id=request_id
                )
                
                turn_latency = int((time.time() - turn_start) * 1000)
                
                # Extract the response text
                if current_to == "openai":
                    response_text = response.get("output", "")
                elif current_to == "manus":
                    response_text = response.get("result", "")
                else:
                    response_text = response.get("output") or response.get("result", "")
                
                # Add to transcript
                transcript.append({
                    "turn": turn,
                    "from": current_from,
                    "to": current_to,
                    "message": current_message,
                    "response": response_text,
                    "latency_ms": turn_latency,
                    "timestamp": time.time()
                })
                
                logger.info(
                    "Bridge turn completed",
                    extra={
                        "request_id": request_id,
                        "turn": turn,
                        "from": current_from,
                        "to": current_to,
                        "latency_ms": turn_latency
                    }
                )
                
                # Prepare for next turn (swap agents)
                current_message = response_text
                current_from, current_to = current_to, current_from
            
            except Exception as e:
                turn_latency = int((time.time() - turn_start) * 1000)
                
                logger.error(
                    "Bridge turn failed",
                    extra={
                        "request_id": request_id,
                        "turn": turn,
                        "from": current_from,
                        "to": current_to,
                        "latency_ms": turn_latency,
                        "error": str(e)
                    }
                )
                
                return {
                    "ok": False,
                    "error": str(e),
                    "transcript": transcript,
                    "failed_at_turn": turn
                }
        
        total_latency = int((time.time() - start_time) * 1000)
        
        logger.info(
            "Agent bridge session completed",
            extra={
                "request_id": request_id,
                "total_turns": len(transcript),
                "total_latency_ms": total_latency
            }
        )
        
        return {
            "ok": True,
            "request_id": request_id,
            "transcript": transcript,
            "total_turns": len(transcript),
            "total_latency_ms": total_latency
        }
    
    def _invoke_agent(
        self,
        agent_id: str,
        agent: dict,
        message: str,
        request_id: str
    ) -> Dict[str, Any]:
        """
        Invoke a specific agent.
        
        Args:
            agent_id: Agent identifier
            agent: Agent configuration
            message: Message to send
            request_id: Request ID for tracking
        
        Returns:
            Agent response
        """
        if agent_id == "openai":
            # Call OpenAI relay
            endpoint = agent.get("endpoint")
            resp = requests.post(
                endpoint,
                json={"message": message},
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()
        
        elif agent_id == "manus":
            # Call Manus adapter
            return invoke_manus(message, context={"request_id": request_id})
        
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
            return resp.json()


# Global singleton instance
_bridge = AgentBridgeService()


def get_bridge() -> AgentBridgeService:
    """Get the global agent bridge instance."""
    return _bridge

