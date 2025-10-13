from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.database import db


class AgentPerformance(db.Model):
    __tablename__ = "agent_performance"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = db.Column(db.String(36), db.ForeignKey("agents.id"), nullable=False, index=True)
    agent = db.relationship("Agent", back_populates="performance_metrics")

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

