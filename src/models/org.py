"""
Organization model for multi-tenant support in Brikk infrastructure.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer
from sqlalchemy.orm import relationship
from src.database.db import db


class Organization(db.Model):
    """Organization model for multi-tenant API key management."""
    
    __tablename__ = 'organizations'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Contact information
    contact_email = Column(String(255), nullable=True)
    contact_name = Column(String(255), nullable=True)
    
    # Billing and limits
    monthly_request_limit = Column(Integer, default=10000, nullable=False)
    current_month_requests = Column(Integer, default=0, nullable=False)
    
    # Relationships
    agents = relationship("Agent", back_populates="organization", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="organization", cascade="all, delete-orphan")
    workflows = relationship("Workflow", back_populates="organization", cascade="all, delete-orphan")
    webhooks = relationship("Webhook", back_populates="organization", cascade="all, delete-orphan")
    balance = relationship("OrgBalance", uselist=False, back_populates="organization", cascade="all, delete-orphan")
    reputation_scores = relationship("ReputationScore", back_populates="organization", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Organization {self.name} ({self.slug})>'
    
    def to_dict(self):
        """Convert organization to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'contact_email': self.contact_email,
            'contact_name': self.contact_name,
            'monthly_request_limit': self.monthly_request_limit,
            'current_month_requests': self.current_month_requests,
            'agent_count': len(self.agents) if self.agents else 0,
            'api_key_count': len([k for k in self.api_keys if k.is_active]) if self.api_keys else 0
        }
    
    @classmethod
    def get_by_slug(cls, slug):
        """Get organization by slug."""
        return cls.query.filter_by(slug=slug, is_active=True).first()
    
    def increment_request_count(self):
        """Increment monthly request count."""
        self.current_month_requests += 1
        db.session.commit()
    
    def reset_monthly_requests(self):
        """Reset monthly request count (called by scheduled job)."""
        self.current_month_requests = 0
        db.session.commit()
    
    def is_within_limits(self):
        """Check if organization is within monthly request limits."""
        return self.current_month_requests < self.monthly_request_limit

