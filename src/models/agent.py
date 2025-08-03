from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class Agent(db.Model):
    """AI Agent model for the Brikk registry"""
    __tablename__ = 'agents'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    organization = db.Column(db.String(100), nullable=False)
    framework = db.Column(db.String(50))  # LangChain, AutoGPT, etc.
    capabilities = db.Column(db.JSON)  # List of capabilities
    endpoints = db.Column(db.JSON)  # API endpoints for communication
    status = db.Column(db.String(20), default='active')  # active, inactive, maintenance
    api_key = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')
    sent_transactions = db.relationship('Transaction', foreign_keys='Transaction.sender_id', backref='sender_agent', lazy='dynamic')
    received_transactions = db.relationship('Transaction', foreign_keys='Transaction.receiver_id', backref='receiver_agent', lazy='dynamic')
    
    def __repr__(self):
        return f'<Agent {self.name} ({self.organization})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'organization': self.organization,
            'framework': self.framework,
            'capabilities': self.capabilities,
            'endpoints': self.endpoints,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None
        }

class Message(db.Model):
    """Agent-to-agent messages"""
    __tablename__ = 'messages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = db.Column(db.String(36), db.ForeignKey('agents.id'), nullable=False)
    receiver_id = db.Column(db.String(36), db.ForeignKey('agents.id'), nullable=False)
    message_type = db.Column(db.String(50), nullable=False)  # coordination, request, response, etc.
    content = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), default='sent')  # sent, delivered, read, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Message {self.id} from {self.sender_id} to {self.receiver_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'message_type': self.message_type,
            'content': self.content,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None
        }

class Transaction(db.Model):
    """Agent-to-agent transactions"""
    __tablename__ = 'transactions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sender_id = db.Column(db.String(36), db.ForeignKey('agents.id'), nullable=False)
    receiver_id = db.Column(db.String(36), db.ForeignKey('agents.id'), nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  # payment, resource_share, etc.
    amount = db.Column(db.Float)  # For payments
    currency = db.Column(db.String(10), default='USD')
    resource_type = db.Column(db.String(50))  # For resource sharing
    resource_data = db.Column(db.JSON)
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed, cancelled
    stripe_payment_intent_id = db.Column(db.String(100))  # For Stripe integration
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Transaction {self.id} from {self.sender_id} to {self.receiver_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'transaction_type': self.transaction_type,
            'amount': self.amount,
            'currency': self.currency,
            'resource_type': self.resource_type,
            'resource_data': self.resource_data,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class CoordinationSession(db.Model):
    """Multi-agent coordination sessions"""
    __tablename__ = 'coordination_sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    coordinator_id = db.Column(db.String(36), db.ForeignKey('agents.id'), nullable=False)
    participants = db.Column(db.JSON)  # List of agent IDs
    session_type = db.Column(db.String(50), nullable=False)  # workflow, auction, negotiation, etc.
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    session_metadata = db.Column(db.JSON)  # Session-specific data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    coordinator = db.relationship('Agent', backref='coordinated_sessions')
    
    def __repr__(self):
        return f'<CoordinationSession {self.name} ({self.id})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'coordinator_id': self.coordinator_id,
            'participants': self.participants,
            'session_type': self.session_type,
            'status': self.status,
            'session_metadata': self.session_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
