# -*- coding: utf-8 -*-
"""
Discovery Models

Defines the database models for agent service discovery and registration.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.infra.db import db


class AgentService(db.Model):
    """Represents a service offered by an agent"""
    __tablename__ = "agent_services"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    name = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    agent = relationship("Agent", back_populates="services")
    capabilities = relationship(
        "AgentCapability",
        back_populates="service",
        cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AgentService {self.name} for agent {self.agent_id}>"


class AgentCapability(db.Model):
    """Represents a capability of an agent service"""
    __tablename__ = "agent_capabilities"

    id = Column(Integer, primary_key=True)
    service_id = Column(
        Integer,
        ForeignKey("agent_services.id"),
        nullable=False)
    name = Column(String(255), nullable=False)

    service = relationship("AgentService", back_populates="capabilities")

    def __repr__(self):
        return f"<AgentCapability {self.name} for service {self.service_id}>"
