# -*- coding: utf-8 -*-

"""
Workflow Execution Model

Represents an execution of a multi-step coordination workflow.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database import db


class WorkflowExecution(db.Model):
    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    workflow = relationship("Workflow", back_populates="executions")

    # pending, running, completed, failed
    status = Column(String, nullable=False, default="pending")
    context = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<WorkflowExecution(id={self.id}, status=\"{self.status}\")>"
