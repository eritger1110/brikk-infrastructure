"""
Webhook Models

Defines the database models for webhook subscriptions and events.
"""

from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database import db

class Webhook(db.Model):
    """Represents a webhook subscription"""
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    url = Column(String(2048), nullable=False)
    secret = Column(String(255), nullable=False)
    events = Column(JSON, nullable=False, default=[])
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="webhooks")
    webhook_events = relationship("WebhookEvent", back_populates="webhook", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Webhook {self.id} for org {self.organization_id}>"

class WebhookEvent(db.Model):
    """Represents a single webhook event delivery attempt"""
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id"), nullable=False)
    event_type = Column(String(255), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # pending, success, failed
    retry_count = Column(Integer, default=0, nullable=False)
    response_status_code = Column(Integer)
    response_body = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    webhook = relationship("Webhook", back_populates="webhook_events")

    def __repr__(self):
        return f"<WebhookEvent {self.id} for webhook {self.webhook_id}>"

