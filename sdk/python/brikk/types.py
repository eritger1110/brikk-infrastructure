# -*- coding: utf-8 -*-
"""Type definitions for the Brikk SDK."""

from typing import Any, Dict, List, Optional, TypedDict
from typing_extensions import NotRequired


class Agent(TypedDict):
    """Agent resource type."""
    id: str
    name: str
    org_id: str
    created_at: NotRequired[str]
    updated_at: NotRequired[str]


class CoordinationMessage(TypedDict):
    """Coordination message envelope."""
    version: str
    message_id: str
    ts: str
    type: str
    sender: Dict[str, str]
    recipient: Dict[str, str]
    payload: Dict[str, Any]
    ttl_ms: int


class Transaction(TypedDict):
    """Economy transaction record."""
    id: str
    org_id: str
    type: str
    amount: int
    meta: Dict[str, Any]
    created_at: str


class ReputationScore(TypedDict):
    """Reputation score for an agent."""
    agent_id: str
    score: float
    total_interactions: int
    positive_feedback: int
    negative_feedback: int


class HealthStatus(TypedDict):
    """Health check response."""
    status: str
    timestamp: NotRequired[str]
    version: NotRequired[str]

