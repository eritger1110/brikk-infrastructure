# -*- coding: utf-8 -*-
"""
API Gateway models for OAuth2, API keys, and audit logging.

These models support Stage 5 API Gateway functionality:
- OrgApiKey: Scoped API keys for external developers
- OAuthClient: OAuth2 client registrations
- OAuthToken: OAuth2 access/refresh token tracking
- ApiAuditLog: Audit trail for all API requests
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.database import db


class OrgApiKey(db.Model):
    """Scoped API keys for organizations.
    
    Supports tiered access control with scope-based permissions.
    Keys are stored as hashes for security.
    """
    
    __tablename__ = "org_api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    key_hash = Column(String(255), nullable=False)
    scopes = Column(ARRAY(String()), nullable=False, default=list)
    tier = Column(String(32), nullable=False, default="FREE")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f'<OrgApiKey {self.name} org={self.org_id} tier={self.tier}>'
    
    def is_active(self):
        """Check if the API key is active (not revoked)."""
        return self.revoked_at is None
    
    def has_scope(self, scope):
        """Check if the key has a specific scope."""
        return scope in self.scopes or "*" in self.scopes
    
    def to_dict(self, include_hash=False):
        """Convert to dictionary for API responses."""
        data = {
            'id': str(self.id),
            'org_id': str(self.org_id),
            'name': self.name,
            'scopes': self.scopes,
            'tier': self.tier,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'is_active': self.is_active()
        }
        if include_hash:
            data['key_hash'] = self.key_hash
        return data


class OAuthClient(db.Model):
    """OAuth2 client registrations.
    
    Supports client credentials flow for machine-to-machine authentication.
    Can be extended to support authorization code flow for user-granted access.
    """
    
    __tablename__ = "oauth_clients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    client_id = Column(String(80), unique=True, nullable=False)
    client_secret_hash = Column(String(255), nullable=False)
    grant_types = Column(ARRAY(String()), nullable=False, default=list)
    redirect_uris = Column(ARRAY(String()), nullable=False, default=list)
    scopes = Column(ARRAY(String()), nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    
    # Phase 6: Relationship to agents
    agents = relationship('Agent', back_populates='oauth_client', foreign_keys='Agent.oauth_client_id')
    
    def __repr__(self):
        return f'<OAuthClient {self.client_id} org={self.org_id}>'
    
    def is_active(self):
        """Check if the client is active (not revoked)."""
        return self.revoked_at is None
    
    def supports_grant_type(self, grant_type):
        """Check if the client supports a specific grant type."""
        return grant_type in self.grant_types
    
    def has_scope(self, scope):
        """Check if the client has a specific scope."""
        return scope in self.scopes or "*" in self.scopes
    
    def to_dict(self, include_secret=False):
        """Convert to dictionary for API responses."""
        data = {
            'id': str(self.id),
            'org_id': str(self.org_id),
            'client_id': self.client_id,
            'grant_types': self.grant_types,
            'redirect_uris': self.redirect_uris,
            'scopes': self.scopes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'is_active': self.is_active()
        }
        if include_secret:
            data['client_secret_hash'] = self.client_secret_hash
        return data


class OAuthToken(db.Model):
    """OAuth2 access and refresh tokens.
    
    Tracks issued tokens for validation and revocation.
    Supports both access and refresh token types.
    """
    
    __tablename__ = "oauth_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(String(80), index=True, nullable=False)
    org_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    subject = Column(String(120), nullable=True)
    scopes = Column(ARRAY(String()), nullable=False, default=list)
    token_type = Column(String(16), nullable=False, default="access")
    issued_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f'<OAuthToken {self.id} client={self.client_id} type={self.token_type}>'
    
    def is_active(self):
        """Check if the token is active (not revoked and not expired)."""
        if self.revoked_at is not None:
            return False
        return datetime.utcnow() < self.expires_at
    
    def is_expired(self):
        """Check if the token is expired."""
        return datetime.utcnow() >= self.expires_at
    
    def has_scope(self, scope):
        """Check if the token has a specific scope."""
        return scope in self.scopes or "*" in self.scopes
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': str(self.id),
            'client_id': self.client_id,
            'org_id': str(self.org_id),
            'subject': self.subject,
            'scopes': self.scopes,
            'token_type': self.token_type,
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'is_active': self.is_active(),
            'is_expired': self.is_expired()
        }


class ApiAuditLog(db.Model):
    """Audit trail for all API requests.
    
    Captures who (org/key), what (endpoint+method), when, result, and cost.
    Used for security monitoring, debugging, and usage analytics.
    """
    
    __tablename__ = "api_audit_log"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    actor_type = Column(String(16), nullable=False)  # api_key|oauth|hmac|anon
    actor_id = Column(String(120), nullable=False, index=True)
    auth_method = Column(String(16), nullable=False, server_default='api_key')  # api_key|oauth|hmac
    request_id = Column(String(64), nullable=False)
    method = Column(String(8), nullable=False)
    path = Column(String(256), nullable=False)
    status = Column(Integer, nullable=False)
    cost_units = Column(Integer, nullable=False, default=0)
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<ApiAuditLog {self.method} {self.path} status={self.status}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': str(self.id),
            'org_id': str(self.org_id),
            'actor_type': self.actor_type,
            'actor_id': self.actor_id,
            'auth_method': self.auth_method,
            'request_id': self.request_id,
            'method': self.method,
            'path': self.path,
            'status': self.status,
            'cost_units': self.cost_units,
            'ip': self.ip,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def log_request(cls, org_id, actor_type, actor_id, request_id, method, path, 
                    status, cost_units=0, ip=None, user_agent=None, auth_method='api_key'):
        """Create a new audit log entry."""
        log = cls(
            org_id=org_id,
            actor_type=actor_type,
            actor_id=actor_id,
            auth_method=auth_method or actor_type,  # Use auth_method if provided, else actor_type
            request_id=request_id,
            method=method,
            path=path[:256],  # Truncate if needed
            status=status,
            cost_units=cost_units,
            ip=ip,
            user_agent=user_agent[:256] if user_agent else None
        )
        db.session.add(log)
        return log

