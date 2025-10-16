"""
Trust layer models for reputation, attestations, and risk management.
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from src.infra.db import db
import uuid


class ReputationSnapshot(db.Model):
    """Reputation score snapshot for an org or agent over a time window."""
    __tablename__ = 'reputation_snapshots'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_type = Column(String(20), nullable=False)  # 'org' or 'agent'
    subject_id = Column(String(36), nullable=False)
    score = Column(Integer, nullable=False)  # 0-100
    window_days = Column(Integer, nullable=False)  # e.g., 7, 30, 90
    components = Column(JSONB, nullable=True)  # breakdown: reliability, commerce, hygiene
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint('score >= 0 AND score <= 100', name='ck_reputation_score_range'),
        CheckConstraint("subject_type IN ('org', 'agent')", name='ck_reputation_subject_type'),
        Index('ix_reputation_subject', 'subject_type', 'subject_id', 'window_days'),
        Index('ix_reputation_created', 'created_at'),
    )

    @classmethod
    def get_latest(cls, subject_type: str, subject_id: str, window_days: int = 30):
        """Get the most recent reputation snapshot for a subject."""
        return cls.query.filter_by(
            subject_type=subject_type,
            subject_id=subject_id,
            window_days=window_days
        ).order_by(cls.created_at.desc()).first()


class Attestation(db.Model):
    """Attestation (web-of-trust) from one org vouching for another org/agent."""
    __tablename__ = 'attestations'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issuer_org_id = Column(Integer, db.ForeignKey('organizations.id'), nullable=False)
    subject_type = Column(String(20), nullable=False)  # 'org' or 'agent'
    subject_id = Column(String(36), nullable=False)
    claim = Column(Text, nullable=False)  # What they're vouching for
    score = Column(Integer, nullable=False)  # 0-100 confidence
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint('score >= 0 AND score <= 100', name='ck_attestation_score_range'),
        CheckConstraint("subject_type IN ('org', 'agent')", name='ck_attestation_subject_type'),
        Index('ix_attestation_subject', 'subject_type', 'subject_id'),
        Index('ix_attestation_issuer', 'issuer_org_id'),
    )

    @classmethod
    def get_active_for_subject(cls, subject_type: str, subject_id: str):
        """Get all active (non-revoked) attestations for a subject."""
        return cls.query.filter_by(
            subject_type=subject_type,
            subject_id=subject_id,
            revoked=False
        ).all()


class RiskEvent(db.Model):
    """Risk event tracking for security and abuse detection."""
    __tablename__ = 'risk_events'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(Integer, db.ForeignKey('organizations.id'), nullable=False)
    event_type = Column(String(50), nullable=False)  # e.g., 'failed_auth', 'rate_limit_exceeded'
    severity = Column(String(10), nullable=False)  # 'low', 'medium', 'high'
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("severity IN ('low', 'medium', 'high')", name='ck_risk_severity'),
        Index('ix_risk_org_created', 'org_id', 'created_at'),
    )

    @classmethod
    def get_recent_for_org(cls, org_id: int, days: int = 7):
        """Get recent risk events for an org within the last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return cls.query.filter(
            cls.org_id == org_id,
            cls.created_at >= cutoff
        ).all()

