# src/models/api_key.py
"""
API Key model for secure per-org/per-agent authentication in Brikk infrastructure.
Uses PBKDF2 hashing for secure, non-reversible API key storage.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship

from src.database import db
from src.services.crypto import generate_api_key, hash_api_key, verify_api_key


class ApiKey(db.Model):
    """API Key model for secure authentication with PBKDF2 hashing."""
    __tablename__ = "api_keys"

    # Identity
    id = Column(Integer, primary_key=True)
    key_id = Column(String(64), unique=True, nullable=False, index=True)      # public identifier
    key_prefix = Column(String(16), nullable=False, index=True)               # first 16 chars

    # Ownership / scope
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    organization = relationship("Organization", back_populates="api_keys")

    # IMPORTANT: match Agent.id = String(36)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True, index=True)
    agent = relationship("Agent", back_populates="api_keys")

    # Secret storage - PBKDF2 hash only (no reversible encryption)
    api_key_hash = Column(Text, nullable=False)                               # PBKDF2 hash of API key

    # Metadata
    name = Column(String(255), nullable=False)
    description = Column(Text)
    scopes = Column(Text)                                                     # optional JSON-encoded list

    # Lifecycle / status
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime)
    last_used_at = Column(DateTime)

    # Security tracking
    total_requests = Column(Integer, default=0, nullable=False)
    failed_requests = Column(Integer, default=0, nullable=False)
    last_failure_at = Column(DateTime)

    # Basic per-key rate hints (does not enforce; limiter uses Redis)
    requests_per_minute = Column(Integer, default=100, nullable=False)
    requests_per_hour = Column(Integer, default=1000, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ApiKey {self.key_prefix}*** ({self.name})>"

    # ---- Factory / crypto helpers -------------------------------------------------

    @classmethod
    def create_api_key(
        cls,
        organization_id: int,
        name: str,
        description: str | None = None,
        agent_id: str | None = None,
        expires_days: int | None = None,
    ) -> tuple["ApiKey", str]:
        """Create and persist a new API key. Returns (ApiKey, PLAINTEXT_API_KEY)."""
        # Generate the API key
        api_key = generate_api_key()
        
        # Hash the API key using PBKDF2
        api_key_hashed = hash_api_key(api_key)
        
        # Create key_id and prefix
        key_id = f"bk_{secrets.token_urlsafe(16)}"
        key_prefix = key_id[:16]

        expires_at = datetime.utcnow() + timedelta(days=expires_days) if expires_days else None

        rec = cls(
            key_id=key_id,
            key_prefix=key_prefix,
            organization_id=organization_id,
            agent_id=agent_id,
            api_key_hash=api_key_hashed,
            name=name,
            description=description,
            expires_at=expires_at,
        )
        db.session.add(rec)
        db.session.commit()
        return rec, api_key

    def verify_api_key(self, provided_api_key: str) -> bool:
        """Verify a provided API key against the stored hash."""
        return verify_api_key(provided_api_key, self.api_key_hash)

    # ---- Convenience ----------------------------------------------------------------

    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        return not (self.expires_at and datetime.utcnow() > self.expires_at)

    def update_usage(self, success: bool = True) -> None:
        self.total_requests += 1
        self.last_used_at = datetime.utcnow()
        if not success:
            self.failed_requests += 1
            self.last_failure_at = datetime.utcnow()
        db.session.commit()

    def disable(self) -> None:
        self.is_active = False
        self.updated_at = datetime.utcnow()
        db.session.commit()

    def get_success_rate(self) -> float:
        if self.total_requests == 0:
            return 100.0
        ok = self.total_requests - self.failed_requests
        return round((ok / self.total_requests) * 100.0, 2)

    def to_dict(self, include_secret: bool = False) -> dict:
        data = {
            "id": self.id,
            "key_id": self.key_id,
            "key_prefix": self.key_prefix,
            "organization_id": self.organization_id,
            "organization_name": self.organization.name if self.organization else None,
            "agent_id": self.agent_id,
            "agent_name": self.agent.name if self.agent else None,
            "name": self.name,
            "description": self.description,
            "scopes": self.scopes,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.get_success_rate(),
            "requests_per_minute": self.requests_per_minute,
            "requests_per_hour": self.requests_per_hour,
            "is_valid": self.is_valid(),
        }
        # Note: API keys are hashed and cannot be retrieved
        if include_secret:
            data["note"] = "API key is hashed and cannot be retrieved"
        return data

    # ---- Queries --------------------------------------------------------------------

    @classmethod
    def get_by_key_id(cls, key_id: str) -> "ApiKey | None":
        return cls.query.filter_by(key_id=key_id, is_active=True).first()

    @classmethod
    def get_by_organization(cls, organization_id: int, active_only: bool = True) -> list["ApiKey"]:
        q = cls.query.filter_by(organization_id=organization_id)
        if active_only:
            q = q.filter_by(is_active=True)
        return q.all()

    @classmethod
    def authenticate_api_key(cls, provided_api_key: str) -> "ApiKey | None":
        """Authenticate an API key and return the ApiKey record if valid."""
        # Extract key_id from the API key if it has the brikk_ prefix
        if provided_api_key.startswith('brikk_'):
            # For now, we'll need to check all active keys since we can't reverse the hash
            # In production, you might want to add an index or use a different approach
            active_keys = cls.query.filter_by(is_active=True).all()
            for api_key_record in active_keys:
                if api_key_record.verify_api_key(provided_api_key) and api_key_record.is_valid():
                    return api_key_record
        return None
