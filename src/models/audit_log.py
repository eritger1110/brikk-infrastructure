# src/models/audit_log.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.types import JSON as SA_JSON  # generic JSON that works on SQLite & Postgres
from ..database.db import db

class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, nullable=True)
    actor_user_id = Column(Integer, nullable=True)

    action = Column(String(120), nullable=False)          # e.g., "agent.created"
    resource_type = Column(String(64), nullable=False)    # e.g., "agent"
    resource_id = Column(String(64), nullable=True)
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)

    # attribute name must NOT be 'metadata' (reserved). Keep column name 'metadata' though.
    meta = Column("metadata", SA_JSON, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
