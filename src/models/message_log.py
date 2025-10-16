# -*- coding: utf-8 -*-
# src/models/message_log.py
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.infra.db import db
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text


class MessageLog(db.Model):
    """Message Log Model for Stage 1 Agent Communication"""
    __tablename__ = "message_logs"

    # Primary key
    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(
            uuid.uuid4()))

    # Owner and agent references
    owner_id = db.Column(db.String(36), nullable=False, index=True)
    sender_id = db.Column(db.String(36), nullable=True, index=True)  # Agent ID
    receiver_id = db.Column(
        db.String(36),
        nullable=True,
        index=True)  # Agent ID

    # Message content - use JSONB for PostgreSQL, fallback to Text for SQLite
    request_payload = db.Column(
        JSONB().with_variant(
            Text, "sqlite"), nullable=False)
    response_payload = db.Column(
        JSONB().with_variant(
            Text, "sqlite"), nullable=True)

    # Status tracking
    status = db.Column(
        db.String(20),
        nullable=False,
        default="success")  # success, error

    # Timestamps
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    def __init__(self, owner_id: str,
                 request_payload: Dict[str, Any], **kwargs):
        self.owner_id = owner_id
        self.request_payload = request_payload
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "request_payload": self.request_payload,
            "response_payload": self.response_payload,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<MessageLog {self.id} owner={self.owner_id} status={self.status}>"
