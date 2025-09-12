# src/models/agent.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from src.database.db import db
import uuid
import json

db = SQLAlchemy()

# ---------------------------
# Purchase (orders / receipts)
# ---------------------------
class Purchase(db.Model):
    """
    Minimal purchase record used to associate a user/subscription with a
    human-friendly order reference that we can surface in emails and the UI.
    """
    __tablename__ = "purchases"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Professional-looking order reference (e.g., BRK-ABC1234...)
    order_ref = db.Column(db.String(32), unique=True, nullable=False, index=True)

    # Who bought it (we store email; you can add user_id if you want)
    email = db.Column(db.String(255), index=True, nullable=False)

    # Stripe pointers (optional but useful)
    stripe_customer_id = db.Column(db.String(64), index=True)
    stripe_subscription_id = db.Column(db.String(64), index=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "order_ref": self.order_ref,
            "email": self.email,
            "stripe_customer_id": self.stripe_customer_id,
            "stripe_subscription_id": self.stripe_subscription_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------
# Existing models (unchanged)
# ---------------------------
class Agent(db.Model):
    """Enterprise AI Agent Model for Brikk Coordination Platform"""
    __tablename__ = 'agents'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    language = db.Column(db.String(50), nullable=False)  # python, nodejs, java, go, rust, csharp
    version = db.Column(db.String(20), default='1.0.0')
    status = db.Column(db.String(20), default='active')  # active, inactive, busy, error
    
    # Agent Capabilities
    capabilities = db.Column(db.Text)  # JSON string of capabilities
    specialization = db.Column(db.String(200))
    performance_score = db.Column(db.Float, default=0.0)
    
    # Connection Information
    endpoint_url = db.Column(db.String(500))
    api_key = db.Column(db.String(100))
    last_seen = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Metrics
    total_coordinations = db.Column(db.Integer, default=0)
    successful_coordinations = db.Column(db.Integer, default=0)
    average_response_time = db.Column(db.Float, default=0.0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __init__(self, name, language, **kwargs):
        self.name = name
        self.language = language
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def get_capabilities(self):
        """Get capabilities as Python list"""
        if self.capabilities:
            try:
                return json.loads(self.capabilities)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_capabilities(self, capabilities_list):
        """Set capabilities from Python list"""
        self.capabilities = json.dumps(capabilities_list)
    
    def update_performance(self, response_time, success=True):
        """Update agent performance metrics"""
        self.total_coordinations += 1
        if success:
            self.successful_coordinations += 1
        
        # Update average response time
        if self.total_coordinations == 1:
            self.average_response_time = response_time
        else:
            self.average_response_time = (
                (self.average_response_time * (self.total_coordinations - 1) + response_time) 
                / self.total_coordinations
            )
        
        # Calculate performance score (0-100)
        success_rate = self.successful_coordinations / self.total_coordinations
        response_score = max(0, 100 - (self.average_response_time / 10))  # Penalize slow responses
        self.performance_score = (success_rate * 70) + (min(response_score, 30))
        
        self.last_seen = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self):
        """Convert agent to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'language': self.language,
            'version': self.version,
            'status': self.status,
            'capabilities': self.get_capabilities(),
            'specialization': self.specialization,
            'performance_score': round(self.performance_score, 2),
            'endpoint_url': self.endpoint_url,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'total_coordinations': self.total_coordinations,
            'successful_coordinations': self.successful_coordinations,
            'success_rate': round((self.successful_coordinations / max(self.total_coordinations, 1)) * 100, 2),
            'average_response_time': round(self.average_response_time, 2),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Coordination(db.Model):
    """Agent Coordination Transaction Model"""
    __tablename__ = 'coordinations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_type = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    
    # Coordination Details
    initiator_agent_id = db.Column(db.String(36), db.ForeignKey('agents.id'))
    participating_agents = db.Column(db.Text)  # JSON array of agent IDs
    workflow_steps = db.Column(db.Text)  # JSON array of workflow steps
    
    # Performance Metrics
    start_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime)
    total_duration = db.Column(db.Float)  # in milliseconds
    
    # Results
    result_data = db.Column(db.Text)  # JSON string of results
    error_message = db.Column(db.Text)
    
    # Security and Compliance
    security_level = db.Column(db.String(20), default='standard')  # basic, standard, elevated, administrative
    audit_trail = db.Column(db.Text)  # JSON array of audit events
    
    def __init__(self, workflow_type, initiator_agent_id, **kwargs):
        self.workflow_type = workflow_type
        self.initiator_agent_id = initiator_agent_id
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def get_participating_agents(self):
        """Get participating agents as Python list"""
        if self.participating_agents:
            try:
                return json.loads(self.participating_agents)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_participating_agents(self, agent_ids):
        """Set participating agents from Python list"""
        self.participating_agents = json.dumps(agent_ids)
    
    def get_workflow_steps(self):
        """Get workflow steps as Python list"""
        if self.workflow_steps:
            try:
                return json.loads(self.workflow_steps)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_workflow_steps(self, steps):
        """Set workflow steps from Python list"""
        self.workflow_steps = json.dumps(steps)
    
    def get_result_data(self):
        """Get result data as Python dict"""
        if self.result_data:
            try:
                return json.loads(self.result_data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_result_data(self, data):
        """Set result data from Python dict"""
        self.result_data = json.dumps(data)
    
    def complete_coordination(self, result_data, success=True):
        """Mark coordination as completed"""
        self.end_time = datetime.now(timezone.utc)
        self.total_duration = (self.end_time - self.start_time).total_seconds() * 1000  # milliseconds
        self.status = 'completed' if success else 'failed'
        self.set_result_data(result_data)
    
    def to_dict(self):
        """Convert coordination to dictionary for API responses"""
        return {
            'id': self.id,
            'workflow_type': self.workflow_type,
            'status': self.status,
            'initiator_agent_id': self.initiator_agent_id,
            'participating_agents': self.get_participating_agents(),
            'workflow_steps': self.get_workflow_steps(),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_duration': self.total_duration,
            'result_data': self.get_result_data(),
            'error_message': self.error_message,
            'security_level': self.security_level
        }


class SecurityEvent(db.Model):
    """Security and Audit Event Model"""
    __tablename__ = 'security_events'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = db.Column(db.String(50), nullable=False)  # access_attempt, data_access, encryption, etc.
    severity = db.Column(db.String(20), default='info')  # info, warning, error, critical
    
    # Event Details
    user_id = db.Column(db.String(100))
    agent_id = db.Column(db.String(36), db.ForeignKey('agents.id'))
    resource_accessed = db.Column(db.String(200))
    access_granted = db.Column(db.Boolean, default=False)
    
    # Security Context
    security_level_required = db.Column(db.String(20))
    security_level_provided = db.Column(db.String(20))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    
    # Event Data
    event_data = db.Column(db.Text)  # JSON string of additional event data
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __init__(self, event_type, **kwargs):
        self.event_type = event_type
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def get_event_data(self):
        """Get event data as Python dict"""
        if self.event_data:
            try:
                return json.loads(self.event_data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_event_data(self, data):
        """Set event data from Python dict"""
        self.event_data = json.dumps(data)
    
    def to_dict(self):
        """Convert security event to dictionary for API responses"""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'severity': self.severity,
            'user_id': self.user_id,
            'agent_id': self.agent_id,
            'resource_accessed': self.resource_accessed,
            'access_granted': self.access_granted,
            'security_level_required': self.security_level_required,
            'security_level_provided': self.security_level_provided,
            'ip_address': self.ip_address,
            'event_data': self.get_event_data(),
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
