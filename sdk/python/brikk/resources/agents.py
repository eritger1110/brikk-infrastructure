# -*- coding: utf-8 -*-
"""Agent management resources."""

from typing import TYPE_CHECKING, Dict, List, Optional, Any

if TYPE_CHECKING:
    from .._http import HTTPClient

from ..types import Agent


class AgentsResource:
    """Agent management operations."""

    def __init__(self, http_client: "HTTPClient"):
        self._http = http_client

    def list(self, org_id: Optional[str] = None) -> List[Agent]:
        """List all agents for an organization.

        Args:
            org_id: Organization ID (optional if set in client)

        Returns:
            List of agent objects

        Example:
            >>> agents = client.agents.list(org_id="org_123")
            >>> for agent in agents:
            ...     print(agent['name'])
        """
        params = {}
        if org_id:
            params["org_id"] = org_id
        response = self._http.get("/api/v1/agents", params=params)
        return response.get("agents", [])

    def create(
        self,
        name: str,
        org_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Agent:
        """Create a new agent.

        Args:
            name: Agent name
            org_id: Organization ID
            metadata: Optional metadata dict

        Returns:
            Created agent object

        Example:
            >>> agent = client.agents.create(
            ...     name="My Agent",
            ...     org_id="org_123",
            ...     metadata={"version": "1.0"}
            ... )
        """
        data = {
            "name": name,
            "org_id": org_id,
        }
        if metadata:
            data["metadata"] = metadata
        return self._http.post("/api/v1/agents", json_data=data)

    def get(self, agent_id: str) -> Agent:
        """Get agent by ID.

        Args:
            agent_id: Agent ID

        Returns:
            Agent object

        Example:
            >>> agent = client.agents.get("agent_123")
        """
        return self._http.get(f"/api/v1/agents/{agent_id}")

