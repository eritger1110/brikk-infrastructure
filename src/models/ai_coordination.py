# src/models/ai_coordination.py

from src.database import db
from sqlalchemy import Column, Integer, String, Float, ForeignKey

class AgentPerformance(db.Model):
    __tablename__ = 'agent_performance'

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(36), ForeignKey('agents.id'), nullable=False)
    workflow_id = Column(Integer, ForeignKey('workflows.id'), nullable=False)
    execution_time = Column(Float, nullable=False)
    success_rate = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)

    agent = db.relationship('Agent', back_populates='performance_metrics')
    workflow = db.relationship('Workflow', back_populates='performance_metrics')

class CoordinationStrategy(db.Model):
    __tablename__ = 'coordination_strategy'

    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey('workflows.id'), nullable=False, unique=True)
    optimized_step_order = Column(db.JSON, nullable=False)
    recommended_agents = Column(db.JSON, nullable=False)

    workflow = db.relationship('Workflow', back_populates='coordination_strategy')

