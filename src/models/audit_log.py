# -*- coding: utf-8 -*-
# src/models/audit_log.py
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import Column, String, DateTime
# generic JSON that works on SQLite & Postgres
from sqlalchemy.types import JSON as SA_JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text
from src.infra.db import db


class AuditLog(db.Model):
    """Audit Log Model for Stage 1 - tracks all user actions"""
    __tablename__ = "audit_logs"

    # Use UUID for primary key to match Stage 1 requirements
    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(
            uuid.uuid4()))

    # Actor (user performing the action)
    actor_id = Column(String(36), nullable=False, index=True)

    # Action details
    # e.g., "agent.created", "echo.sent"
    action = Column(String(120), nullable=False)
    # e.g., "agent", "message"
    resource_type = Column(String(64), nullable=True)
    # UUID of the resource
    resource_id = Column(String(36), nullable=True)

    # Metadata - use JSONB for PostgreSQL, fallback to Text for SQLite
    details = Column(JSONB().with_variant(Text, "sqlite"), nullable=True)

    # Timestamp with timezone
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    def __init__(self, actor_id: str, action: str, **kwargs):
        self.actor_id = actor_id
        self.action = action
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "actor_id": self.actor_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<AuditLog {self.id} actor={self.actor_id} action={self.action}>"
