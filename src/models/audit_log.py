from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, DateTime
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
try:
    from sqlalchemy.dialects.postgresql import JSONB as JSONType  # in case you switch DBs later
except Exception:
    JSONType = SQLITE_JSON

from ..database.db import db

class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True)
    org_id = Column(Integer, nullable=True)
    actor_user_id = Column(Integer, nullable=True)
    action = Column(String(120), nullable=False)          # e.g., "agent.created"
    resource_type = Column(String(64), nullable=False)    # e.g., "agent"
    resource_id = Column(String(64), nullable=True)
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    metadata = Column(JSONType, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
