# -*- coding: utf-8 -*-
"""Reputation and scoring resources."""

from typing import TYPE_CHECKING, Dict, List, Any, Optional

if TYPE_CHECKING:
    from .._http import HTTPClient

from ..types import ReputationScore


class ReputationResource:
    """Reputation and agent scoring operations."""

    def __init__(self, http_client: "HTTPClient"):
        self._http = http_client

    def get_summary(self, org_id: str) -> Dict[str, Any]:
        """Get reputation summary for an organization.

        Args:
            org_id: Organization ID

        Returns:
            Reputation summary dict

        Example:
            >>> summary = client.reputation.get_summary("org_123")
            >>> print(summary['average_score'])
        """
        return self._http.get("/api/v1/reputation/summary", params={"org_id": org_id})

    def list_agent_scores(self, org_id: str) -> List[ReputationScore]:
        """List reputation scores for all agents in an organization.

        Args:
            org_id: Organization ID

        Returns:
            List of reputation score objects

        Example:
            >>> scores = client.reputation.list_agent_scores("org_123")
            >>> for score in scores:
            ...     print(f"{score['agent_id']}: {score['score']}")
        """
        response = self._http.get("/api/v1/reputation/agents", params={"org_id": org_id})
        return response.get("agents", [])

    def get_agent_score(self, agent_id: str, org_id: Optional[str] = None) -> ReputationScore:
        """Get reputation score for a specific agent.

        Args:
            agent_id: Agent ID
            org_id: Organization ID (optional)

        Returns:
            Reputation score object

        Example:
            >>> score = client.reputation.get_agent_score("agent_123")
        """
        params = {"agent_id": agent_id}
        if org_id:
            params["org_id"] = org_id
        response = self._http.get("/api/v1/reputation/agents", params=params)
        agents = response.get("agents", [])
        for agent in agents:
            if agent.get("agent_id") == agent_id:
                return agent
        return {}

