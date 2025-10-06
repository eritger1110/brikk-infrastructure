# src/models/api_key.py
"""
API Key model for secure per-org/per-agent authentication in Brikk infrastructure.
"""
from __future__ import annotations

import os
import secrets
import hashlib
from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from cryptography.fernet import Fernet

from src.database.db import db


class ApiKey(db.Model):
    """API Key model for secure HMAC-based authentication."""
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

    # Secret storage
    encrypted_secret = Column(Text, nullable=False)                           # Fernet-encrypted HMAC secret
    secret_hash = Column(String(128), nullable=False, index=True)             # SHA-256(secret)

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
    def generate_key_pair(cls) -> tuple[str, str]:
        """Generate a new (key_id, secret)."""
        key_id = f"bk_{secrets.token_urlsafe(32)}"
        secret = secrets.token_urlsafe(48)
        return key_id, secret

    @classmethod
    def create_api_key(
        cls,
        organization_id: int,
        name: str,
        description: str | None = None,
        agent_id: str | None = None,
        expires_days: int | None = None,
    ) -> tuple["ApiKey", str]:
        """Create and persist a new API key. Returns (ApiKey, PLAINTEXT_SECRET)."""
        key_id, secret = cls.generate_key_pair()

        enc_key = os.environ.get("BRIKK_ENCRYPTION_KEY")
        if not enc_key:
            # In production this MUST be provided; for dev we generate one on the fly.
            enc_key = Fernet.generate_key()  # type: ignore[assignment]
        fernet = Fernet(enc_key.encode() if isinstance(enc_key, str) else enc_key)

        encrypted_secret = fernet.encrypt(secret.encode()).decode()
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()

        expires_at = datetime.utcnow() + timedelta(days=expires_days) if expires_days else None

        rec = cls(
            key_id=key_id,
            key_prefix=key_id[:16],
            organization_id=organization_id,
            agent_id=agent_id,
            encrypted_secret=encrypted_secret,
            secret_hash=secret_hash,
            name=name,
            description=description,
            expires_at=expires_at,
        )
        db.session.add(rec)
        db.session.commit()
        return rec, secret

    def decrypt_secret(self) -> str:
        enc_key = os.environ.get("BRIKK_ENCRYPTION_KEY")
        if not enc_key:
            raise ValueError("BRIKK_ENCRYPTION_KEY not configured")
        fernet = Fernet(enc_key.encode() if isinstance(enc_key, str) else enc_key)
        return fernet.decrypt(self.encrypted_secret.encode()).decode()

    def verify_secret(self, provided_secret: str) -> bool:
        return secrets.compare_digest(
            self.secret_hash, hashlib.sha256(provided_secret.encode()).hexdigest()
        )

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

    def rotate_secret(self) -> str:
        _key_id, new_secret = self.generate_key_pair()
        enc_key = os.environ.get("BRIKK_ENCRYPTION_KEY")
        if not enc_key:
            raise ValueError("BRIKK_ENCRYPTION_KEY not configured")
        fernet = Fernet(enc_key.encode() if isinstance(enc_key, str) else enc_key)
        self.encrypted_secret = fernet.encrypt(new_secret.encode()).decode()
        self.secret_hash = hashlib.sha256(new_secret.encode()).hexdigest()
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return new_secret

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
        if include_secret:
            data["secret"] = self.decrypt_secret()
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
