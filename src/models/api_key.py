"""
API Key model for secure per-org/per-agent authentication in Brikk infrastructure.
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from cryptography.fernet import Fernet
import os
from src.database.db import db


class ApiKey(db.Model):
    """API Key model for secure HMAC-based authentication."""
    
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True)
    key_id = Column(String(64), unique=True, nullable=False, index=True)  # Public key identifier
    key_prefix = Column(String(16), nullable=False, index=True)  # First 8 chars for identification
    
    # Relationships
    organization_id = Column(Integer, ForeignKey('organizations.id'), nullable=False, index=True)
    organization = relationship("Organization", back_populates="api_keys")
    
    agent_id = Column(Integer, ForeignKey('agents.id'), nullable=True, index=True)  # Optional agent scoping
    agent = relationship("Agent", back_populates="api_keys")
    
    # Encrypted secret storage
    encrypted_secret = Column(Text, nullable=False)  # Encrypted HMAC secret
    secret_hash = Column(String(128), nullable=False, index=True)  # SHA-256 hash for verification
    
    # Key metadata
    name = Column(String(255), nullable=False)  # Human-readable name
    description = Column(Text, nullable=True)
    scopes = Column(Text, nullable=True)  # JSON array of allowed scopes
    
    # Status and lifecycle
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration
    last_used_at = Column(DateTime, nullable=True)
    
    # Security tracking
    total_requests = Column(Integer, default=0, nullable=False)
    failed_requests = Column(Integer, default=0, nullable=False)
    last_failure_at = Column(DateTime, nullable=True)
    
    # Rate limiting
    requests_per_minute = Column(Integer, default=100, nullable=False)
    requests_per_hour = Column(Integer, default=1000, nullable=False)
    
    def __repr__(self):
        return f'<ApiKey {self.key_prefix}*** ({self.name})>'
    
    @classmethod
    def generate_key_pair(cls):
        """Generate a new API key ID and secret."""
        # Generate key ID (public identifier)
        key_id = f"bk_{secrets.token_urlsafe(32)}"
        
        # Generate secret (for HMAC signing)
        secret = secrets.token_urlsafe(48)
        
        return key_id, secret
    
    @classmethod
    def create_api_key(cls, organization_id, name, description=None, agent_id=None, expires_days=None):
        """Create a new API key with encrypted secret storage."""
        key_id, secret = cls.generate_key_pair()
        
        # Create encryption key from environment or generate
        encryption_key = os.environ.get('BRIKK_ENCRYPTION_KEY')
        if not encryption_key:
            # In production, this should be set in environment
            encryption_key = Fernet.generate_key()
        
        # Encrypt the secret
        fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        encrypted_secret = fernet.encrypt(secret.encode()).decode()
        
        # Hash the secret for verification
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        
        # Calculate expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        # Create API key record
        api_key = cls(
            key_id=key_id,
            key_prefix=key_id[:16],  # First 16 chars for identification
            organization_id=organization_id,
            agent_id=agent_id,
            encrypted_secret=encrypted_secret,
            secret_hash=secret_hash,
            name=name,
            description=description,
            expires_at=expires_at
        )
        
        db.session.add(api_key)
        db.session.commit()
        
        # Return the API key record and the plaintext secret (only time it's available)
        return api_key, secret
    
    def decrypt_secret(self):
        """Decrypt and return the HMAC secret."""
        encryption_key = os.environ.get('BRIKK_ENCRYPTION_KEY')
        if not encryption_key:
            raise ValueError("BRIKK_ENCRYPTION_KEY not configured")
        
        fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        return fernet.decrypt(self.encrypted_secret.encode()).decode()
    
    def verify_secret(self, provided_secret):
        """Verify a provided secret against the stored hash."""
        provided_hash = hashlib.sha256(provided_secret.encode()).hexdigest()
        return secrets.compare_digest(self.secret_hash, provided_hash)
    
    def is_valid(self):
        """Check if API key is valid (active and not expired)."""
        if not self.is_active:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        
        return True
    
    def update_usage(self, success=True):
        """Update usage statistics."""
        self.total_requests += 1
        self.last_used_at = datetime.utcnow()
        
        if not success:
            self.failed_requests += 1
            self.last_failure_at = datetime.utcnow()
        
        db.session.commit()
    
    def rotate_secret(self):
        """Rotate the API key secret while keeping the same key_id."""
        _, new_secret = self.generate_key_pair()
        
        # Encrypt new secret
        encryption_key = os.environ.get('BRIKK_ENCRYPTION_KEY')
        if not encryption_key:
            raise ValueError("BRIKK_ENCRYPTION_KEY not configured")
        
        fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        self.encrypted_secret = fernet.encrypt(new_secret.encode()).decode()
        self.secret_hash = hashlib.sha256(new_secret.encode()).hexdigest()
        self.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return new_secret
    
    def disable(self):
        """Disable the API key."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self, include_secret=False):
        """Convert API key to dictionary for API responses."""
        data = {
            'id': self.id,
            'key_id': self.key_id,
            'key_prefix': self.key_prefix,
            'organization_id': self.organization_id,
            'organization_name': self.organization.name if self.organization else None,
            'agent_id': self.agent_id,
            'agent_name': self.agent.name if self.agent else None,
            'name': self.name,
            'description': self.description,
            'scopes': self.scopes,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'total_requests': self.total_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.get_success_rate(),
            'requests_per_minute': self.requests_per_minute,
            'requests_per_hour': self.requests_per_hour,
            'is_valid': self.is_valid()
        }
        
        if include_secret:
            # Only include secret in response when explicitly requested (e.g., during creation)
            data['secret'] = self.decrypt_secret()
        
        return data
    
    def get_success_rate(self):
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 100.0
        
        successful_requests = self.total_requests - self.failed_requests
        return round((successful_requests / self.total_requests) * 100, 2)
    
    @classmethod
    def get_by_key_id(cls, key_id):
        """Get API key by key_id."""
        return cls.query.filter_by(key_id=key_id, is_active=True).first()
    
    @classmethod
    def get_by_organization(cls, organization_id, active_only=True):
        """Get all API keys for an organization."""
        query = cls.query.filter_by(organization_id=organization_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()
