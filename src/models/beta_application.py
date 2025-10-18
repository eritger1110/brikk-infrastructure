"""
Beta Application Model
Stores applications for the private beta program
"""

from datetime import datetime
from src.infra.db import db

class BetaApplication(db.Model):
    """Model for beta program applications"""
    
    __tablename__ = 'beta_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Application details
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    company = db.Column(db.String(255), nullable=True)
    use_case = db.Column(db.Text, nullable=False)
    
    # Status tracking
    status = db.Column(
        db.String(50), 
        nullable=False, 
        default='pending',
        index=True
    )  # pending, approved, rejected, invited
    
    # Metadata
    source = db.Column(db.String(100), nullable=True)  # Where they found us
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    invited_at = db.Column(db.DateTime, nullable=True)
    
    # Admin notes
    admin_notes = db.Column(db.Text, nullable=True)
    reviewed_by = db.Column(db.String(255), nullable=True)
    
    # API key (generated when approved)
    api_key = db.Column(db.String(64), nullable=True, unique=True, index=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'company': self.company,
            'use_case': self.use_case,
            'status': self.status,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'invited_at': self.invited_at.isoformat() if self.invited_at else None,
            'admin_notes': self.admin_notes,
            'reviewed_by': self.reviewed_by
        }
    
    def __repr__(self):
        return f'<BetaApplication {self.email} ({self.status})>'

