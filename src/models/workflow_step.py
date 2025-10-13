# -*- coding: utf-8 -*-

"""
Workflow Step Model

Represents a single step in a multi-step coordination workflow.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database import db


class WorkflowStep(db.Model):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    workflow = relationship("Workflow", back_populates="steps")

    name = Column(String, nullable=False)
    description = Column(String)

    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    agent = relationship("Agent")

    action = Column(String, nullable=False)
    params = Column(JSON)

    order = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<WorkflowStep(id={self.id}, name='{self.name}')>"
