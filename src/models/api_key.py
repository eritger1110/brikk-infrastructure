# -*- coding: utf-8 -*-
"""
API Key model for secure per-org/per-agent authentication in Brikk infrastructure.
Uses Fernet encryption for secure, reversible API key storage.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from cryptography.fernet import Fernet

from src.database import db


def get_fernet():
    """Get Fernet instance from environment key."""
    encryption_key = os.environ.get("BRIKK_ENCRYPTION_KEY")
    if not encryption_key:
        raise ValueError("BRIKK_ENCRYPTION_KEY environment variable not set.")
    return Fernet(encryption_key.encode())


class ApiKey(db.Model):
    """API Key model for secure authentication with Fernet encryption."""
    __tablename__ = "api_keys"

    # Identity
    id = Column(Integer, primary_key=True)
    key_id = Column(String(64), unique=True, nullable=False, index=True)
    key_prefix = Column(String(16), nullable=False, index=True)

    # Ownership / scope
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id"),
        nullable=False,
        index=True)
    organization = relationship("Organization", back_populates="api_keys")

    agent_id = Column(
        String(36),
        ForeignKey("agents.id"),
        nullable=True,
        index=True)
    agent = relationship("Agent", back_populates="api_keys")

    # Secret storage - Fernet encrypted
    api_key_encrypted = Column(Text, nullable=False)

    # Metadata
    name = Column(String(255), nullable=False)
    description = Column(Text)
    scopes = Column(Text)

    # Lifecycle / status
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False)
    expires_at = Column(DateTime)
    last_used_at = Column(DateTime)

    # Security tracking
    total_requests = Column(Integer, default=0, nullable=False)
    failed_requests = Column(Integer, default=0, nullable=False)
    last_failure_at = Column(DateTime)

    # Basic per-key rate hints
    requests_per_minute = Column(Integer, default=100, nullable=False)
    requests_per_hour = Column(Integer, default=1000, nullable=False)

    def __repr__(self) -> str:
        return f"<ApiKey {self.key_prefix}*** ({self.name})>"

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
        fernet = get_fernet()
        api_key = f"brikk_{secrets.token_urlsafe(32)}"
        api_key_encrypted = fernet.encrypt(api_key.encode()).decode()

        key_id = f"bk_{secrets.token_urlsafe(16)}"
        key_prefix = key_id[:16]

        expires_at = datetime.utcnow() + timedelta(days=expires_days) if expires_days else None

        rec = cls(
            key_id=key_id,
            key_prefix=key_prefix,
            organization_id=organization_id,
            agent_id=agent_id,
            api_key_encrypted=api_key_encrypted,
            name=name,
            description=description,
            expires_at=expires_at,
        )
        db.session.add(rec)
        db.session.commit()
        return rec, api_key

    def decrypt_secret(self) -> str:
        """Decrypt the stored API key secret."""
        fernet = get_fernet()
        return fernet.decrypt(self.api_key_encrypted.encode()).decode()

    def rotate_secret(self) -> str:
        """Generate a new secret, encrypt it, and update the record."""
        fernet = get_fernet()
        new_secret = f"brikk_{secrets.token_urlsafe(32)}"
        self.api_key_encrypted = fernet.encrypt(new_secret.encode()).decode()
        self.updated_at = datetime.utcnow()
        db.session.add(self)
        db.session.commit()
        return new_secret

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
        if include_secret:
            data["note"] = "API key is encrypted and cannot be retrieved without the key."
        return data

    @classmethod
    def get_by_key_id(cls, key_id: str) -> "ApiKey | None":
        return cls.query.filter_by(key_id=key_id, is_active=True).first()

    @classmethod
    def get_by_organization(
            cls,
            organization_id: int,
            active_only: bool = True) -> list["ApiKey"]:
        q = cls.query.filter_by(organization_id=organization_id)
        if active_only:
            q = q.filter_by(is_active=True)
        return q.all()

    @classmethod
    def authenticate_api_key(cls, provided_api_key: str) -> "ApiKey | None":
        """Authenticate an API key and return the ApiKey record if valid."""
        active_keys = cls.query.filter_by(is_active=True).all()
        for api_key_record in active_keys:
            try:
                decrypted_secret = api_key_record.decrypt_secret()
                if secrets.compare_digest(
                        provided_api_key,
                        decrypted_secret) and api_key_record.is_valid():
                    return api_key_record
            except Exception:
                continue
        return None
