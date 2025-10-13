# -*- coding: utf-8 -*-
# src/models/agent.py
from __future__ import annotations
from src.models.agent_performance import AgentPerformance

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.database import db
from sqlalchemy.types import TypeDecorator


# ---------------------------------------------------------
# JSON helpers that store Python lists/dicts in TEXT columns
# ---------------------------------------------------------
class JSONList(TypeDecorator):
    """
    Store a Python list in a TEXT column as JSON.
    Always returns a Python list (empty list if null/invalid).
    """
    impl = db.Text
    cache_ok = True

    def process_bind_param(self, value: Optional[List[Any]], dialect):
        if value is None:
            return None
        try:
            return json.dumps(value)
        except Exception:
            return json.dumps([])

    def process_result_value(self, value: Optional[str], dialect):
        if not value:
            return []
        try:
            v = json.loads(value)
            return v if isinstance(v, list) else []
        except Exception:
            return []


class JSONDict(TypeDecorator):
    """
    Store a Python dict in a TEXT column as JSON.
    Always returns a Python dict (empty dict if null/invalid).
    """
    impl = db.Text
    cache_ok = True

    def process_bind_param(self, value: Optional[Dict[str, Any]], dialect):
        if value is None:
            return None
        try:
            return json.dumps(value)
        except Exception:
            return json.dumps({})

    def process_result_value(self, value: Optional[str], dialect):
        if not value:
            return {}
        try:
            v = json.loads(value)
            return v if isinstance(v, dict) else {}
        except Exception:
            return {}


# ---------------------------
# Agent
# ---------------------------
class Agent(db.Model):
    """Enterprise AI Agent Model for Brikk Coordination Platform"""
    __tablename__ = "agents"

    # Identity
    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(
            uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)

    # Core
    language = db.Column(db.String(50), nullable=False)  # e.g., "en"
    version = db.Column(db.String(20), default="1.0.0")
    # active, inactive, busy, error
    status = db.Column(db.String(20), default="active")

    # Descriptive
    description = db.Column(db.Text, nullable=True)      # <'" newly added
    capabilities = db.Column(JSONList)                   # list[str]
    tags = db.Column(JSONList)                            # list[str] (new)

    specialization = db.Column(db.String(200))
    performance_score = db.Column(db.Float, default=0.0)

    # Connection
    endpoint_url = db.Column(db.String(500))
    api_key = db.Column(db.String(100))
    last_seen = db.Column(
        db.DateTime,
        default=lambda: datetime.now(
            timezone.utc))

    # Metrics
    total_coordinations = db.Column(db.Integer, default=0)
    successful_coordinations = db.Column(db.Integer, default=0)
    average_response_time = db.Column(db.Float, default=0.0)

    # Timestamps
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(
            timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    organization_id = db.Column(
        db.String(36),
        db.ForeignKey("organizations.id"),
        nullable=False,
        index=True)
    organization = db.relationship("Organization", back_populates="agents")
    api_keys = db.relationship(
        "ApiKey",
        back_populates="agent",
        cascade="all, delete-orphan")
    services = db.relationship(
        "AgentService",
        back_populates="agent",
        cascade="all, delete-orphan")
    reputation_scores = db.relationship(
        "ReputationScore",
        back_populates="agent",
        cascade="all, delete-orphan")
    performance_metrics = db.relationship(
        "AgentPerformance",
        back_populates="agent",
        cascade="all, delete-orphan")

    def __init__(self, name: str, language: str, **kwargs):
        self.name = name
        self.language = language
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Ensure list fields are lists even if not provided
        if self.capabilities is None:
            self.capabilities = []
        if self.tags is None:
            self.tags = []

    # ---- Back-compat helpers (you can keep using these) ----
    def get_capabilities(self) -> List[str]:
        return self.capabilities or []

    def set_capabilities(self, capabilities_list: List[str]) -> None:
        self.capabilities = capabilities_list or []

    # ---- Metrics helpers ----
    def update_performance(
            self,
            response_time: float,
            success: bool = True) -> None:
        self.total_coordinations += 1
        if success:
            self.successful_coordinations += 1

        if self.total_coordinations == 1:
            self.average_response_time = response_time
        else:
            self.average_response_time = (
                (self.average_response_time *
                 (
                     self.total_coordinations -
                     1) +
                    response_time) /
                self.total_coordinations)

        success_rate = (
            self.successful_coordinations /
            self.total_coordinations if self.total_coordinations else 0.0)
        response_score = max(0.0, 100.0 - (self.average_response_time / 10.0))
        self.performance_score = (success_rate * 70.0) + \
            (min(response_score, 30.0))

        self.last_seen = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        # success rate rounded but safe if totals are zero
        success_rate = (
            (self.successful_coordinations / self.total_coordinations) * 100.0
            if self.total_coordinations else 0.0
        )
        return {
            "id": self.id,
            "name": self.name,
            "language": self.language,
            "version": self.version,
            "status": self.status,
            "description": self.description,
            "capabilities": self.capabilities or [],
            "tags": self.tags or [],
            "specialization": self.specialization,
            "performance_score": round(self.performance_score or 0.0, 2),
            "endpoint_url": self.endpoint_url,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "total_coordinations": self.total_coordinations,
            "successful_coordinations": self.successful_coordinations,
            "success_rate": round(success_rate, 2),
            "average_response_time": round(self.average_response_time or 0.0, 2),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:  # nice for logs
        return f"<Agent {self.id} {self.name!r}>"


# ---------------------------
# Coordination
# ---------------------------
class Coordination(db.Model):
    """Agent Coordination Transaction Model"""
    __tablename__ = "coordinations"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(
            uuid.uuid4()))
    workflow_type = db.Column(db.String(100), nullable=False)
    # pending, running, completed, failed
    status = db.Column(db.String(20), default="pending")

    initiator_agent_id = db.Column(db.String(36), db.ForeignKey("agents.id"))
    participating_agents = db.Column(JSONList)  # list[str]
    workflow_steps = db.Column(JSONList)        # list[dict|str]

    # Performance
    start_time = db.Column(
        db.DateTime,
        default=lambda: datetime.now(
            timezone.utc))
    end_time = db.Column(db.DateTime)
    total_duration = db.Column(db.Float)  # milliseconds

    # Results
    result_data = db.Column(JSONDict)  # dict
    error_message = db.Column(db.Text)

    # Security & audit
    security_level = db.Column(db.String(20), default="standard")
    audit_trail = db.Column(JSONList)  # list[dict]

    def __init__(self, workflow_type: str, initiator_agent_id: str, **kwargs):
        self.workflow_type = workflow_type
        self.initiator_agent_id = initiator_agent_id
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        if self.participating_agents is None:
            self.participating_agents = []
        if self.workflow_steps is None:
            self.workflow_steps = []
        if self.result_data is None:
            self.result_data = {}
        if self.audit_trail is None:
            self.audit_trail = []

    def complete_coordination(
            self, result_data: Dict[str, Any], success: bool = True) -> None:
        self.end_time = datetime.now(timezone.utc)
        self.total_duration = (
            self.end_time - self.start_time).total_seconds() * 1000.0
        self.status = "completed" if success else "failed"
        self.result_data = result_data or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_type": self.workflow_type,
            "status": self.status,
            "initiator_agent_id": self.initiator_agent_id,
            "participating_agents": self.participating_agents or [],
            "workflow_steps": self.workflow_steps or [],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration": self.total_duration,
            "result_data": self.result_data or {},
            "error_message": self.error_message,
            "security_level": self.security_level,
        }


# ---------------------------
# SecurityEvent
# ---------------------------
class SecurityEvent(db.Model):
    """Security and Audit Event Model"""
    __tablename__ = "security_events"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(
            uuid.uuid4()))
    event_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), default="info")

    # Event details
    user_id = db.Column(db.String(100))
    agent_id = db.Column(db.String(36), db.ForeignKey("agents.id"))
    resource_accessed = db.Column(db.String(200))
    access_granted = db.Column(db.Boolean, default=False)

    # Context
    security_level_required = db.Column(db.String(20))
    security_level_provided = db.Column(db.String(20))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))

    # Data
    event_data = db.Column(JSONDict)  # dict
    timestamp = db.Column(
        db.DateTime,
        default=lambda: datetime.now(
            timezone.utc))

    def __init__(self, event_type: str, **kwargs):
        self.event_type = event_type
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        if self.event_data is None:
            self.event_data = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "severity": self.severity,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "resource_accessed": self.resource_accessed,
            "access_granted": self.access_granted,
            "security_level_required": self.security_level_required,
            "security_level_provided": self.security_level_provided,
            "ip_address": self.ip_address,
            "event_data": self.event_data or {},
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
