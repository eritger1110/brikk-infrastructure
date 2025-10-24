# -*- coding: utf-8 -*-
"""
Agent Registry Service

Manages registration and retrieval of AI agents for inter-agent communication.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentRegistryService:
    """
    In-memory registry for AI agents.
    
    In production, this would be backed by a database.
    For the MVP, we use a simple dict for fast iteration.
    """
    
    def __init__(self):
        self._agents: Dict[str, dict] = {}
        logger.info("AgentRegistryService initialized")
    
    def register(self, agent_id: str, agent_data: dict) -> dict:
        """
        Register or update an agent.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_data: Agent configuration including name, type, endpoint, etc.
        
        Returns:
            The registered agent data with metadata
        """
        now = datetime.utcnow().isoformat()
        
        agent_record = {
            "id": agent_id,
            "name": agent_data.get("name", agent_id),
            "type": agent_data.get("type", "http"),
            "endpoint": agent_data.get("endpoint"),
            "expects": agent_data.get("expects", {}),
            "returns": agent_data.get("returns", {}),
            "auth": agent_data.get("auth", {}),
            "metadata": agent_data.get("metadata", {}),
            "registered_at": self._agents.get(agent_id, {}).get("registered_at", now),
            "updated_at": now
        }
        
        self._agents[agent_id] = agent_record
        
        logger.info(
            "Agent registered",
            extra={
                "agent_id": agent_id,
                "agent_name": agent_record["name"],
                "endpoint": agent_record["endpoint"]
            }
        )
        
        return agent_record
    
    def get(self, agent_id: str) -> Optional[dict]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)
    
    def list_all(self) -> List[dict]:
        """List all registered agents."""
        return list(self._agents.values())
    
    def exists(self, agent_id: str) -> bool:
        """Check if an agent is registered."""
        return agent_id in self._agents
    
    def delete(self, agent_id: str) -> bool:
        """Delete an agent from the registry."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info("Agent deleted", extra={"agent_id": agent_id})
            return True
        return False


# Global singleton instance
_registry = AgentRegistryService()


def get_registry() -> AgentRegistryService:
    """Get the global agent registry instance."""
    return _registry

