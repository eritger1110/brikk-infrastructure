# -*- coding: utf-8 -*-
"""
Trust Layer Models (Phase 7 PR-1).

Reputation, Attestations, and Risk Events for network intelligence.
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
from src.database import db
import uuid


class ReputationSnapshot(db.Model):
    """Reputation score snapshot for an org or agent over a time window."""
    __tablename__ = 'reputation_snapshots'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_type = Column(String(10), nullable=False)  # 'org' or 'agent'
    subject_id = Column(String(36), nullable=False)
    score = Column(Integer, nullable=False)  # 0-100
    window = Column(String(10), nullable=False)  # '7d', '30d', '90d'
    reason = Column(JSONB, nullable=False)  # Top factors + weights
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("subject_type IN ('org', 'agent')", name='ck_reputation_subject_type'),
        CheckConstraint("window IN ('7d', '30d', '90d')", name='ck_reputation_window'),
        CheckConstraint('score >= 0 AND score <= 100', name='ck_reputation_score_range'),
        Index('ix_reputation_snapshots_subject', 'subject_type', 'subject_id', 'created_at', postgresql_ops={'created_at': 'DESC'}),
    )
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'subject_type': self.subject_type,
            'subject_id': self.subject_id,
            'score': self.score,
            'window': self.window,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def get_latest(cls, db, subject_type: str, subject_id: str, window: str = '30d'):
        """Get the latest reputation snapshot for a subject."""
        return db.query(cls).filter(
            cls.subject_type == subject_type,
            cls.subject_id == subject_id,
            cls.window == window
        ).order_by(cls.created_at.desc()).first()
    
    @classmethod
    def create_snapshot(cls, db, subject_type: str, subject_id: str, score: int, window: str, reason: dict):
        """Create a new reputation snapshot."""
        snapshot = cls(
            subject_type=subject_type,
            subject_id=subject_id,
            score=score,
            window=window,
            reason=reason
        )
        db.add(snapshot)
        db.commit()
        return snapshot


class Attestation(db.Model):
    """Attestation (web-of-trust) from one org vouching for another org/agent."""
    __tablename__ = 'attestations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issuer_org = Column(String(36), nullable=False)  # Organization ID issuing the attestation
    subject_type = Column(String(10), nullable=False)  # 'org' or 'agent'
    subject_id = Column(String(36), nullable=False)
    scopes = Column(ARRAY(Text), nullable=False)  # e.g., ['reliability', 'quality', 'support']
    weight = Column(Integer, nullable=False, default=1)  # 1-10
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("subject_type IN ('org', 'agent')", name='ck_attestation_subject_type'),
        CheckConstraint('weight >= 1 AND weight <= 10', name='ck_attestation_weight_range'),
        Index('ix_attestations_issuer', 'issuer_org', 'created_at', postgresql_ops={'created_at': 'DESC'}),
        Index('ix_attestations_subject', 'subject_type', 'subject_id'),
    )
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'issuer_org': self.issuer_org,
            'subject_type': self.subject_type,
            'subject_id': self.subject_id,
            'scopes': self.scopes,
            'weight': self.weight,
            'note': self.note,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def get_for_subject(cls, db, subject_type: str, subject_id: str):
        """Get all attestations for a subject."""
        return db.query(cls).filter(
            cls.subject_type == subject_type,
            cls.subject_id == subject_id
        ).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def create_attestation(cls, db, issuer_org: str, subject_type: str, subject_id: str, 
                          scopes: list, weight: int = 1, note: str = None):
        """Create a new attestation."""
        attestation = cls(
            issuer_org=issuer_org,
            subject_type=subject_type,
            subject_id=subject_id,
            scopes=scopes,
            weight=weight,
            note=note
        )
        db.add(attestation)
        db.commit()
        return attestation


class RiskEvent(db.Model):
    """Risk event tracking for security and abuse detection."""
    __tablename__ = 'risk_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(String(36), nullable=False)
    actor_id = Column(Text, nullable=True)  # API key ID, OAuth client ID, etc.
    type = Column(Text, nullable=False)  # 'auth_fail', 'chargeback', 'rate_limit_spike', etc.
    severity = Column(String(10), nullable=False)  # 'low', 'med', 'high'
    meta = Column(JSONB, nullable=True)  # Additional context
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    __table_args__ = (
        CheckConstraint("severity IN ('low', 'med', 'high')", name='ck_risk_event_severity'),
        Index('ix_risk_events_org', 'org_id', 'created_at', postgresql_ops={'created_at': 'DESC'}),
        Index('ix_risk_events_type', 'type', 'created_at', postgresql_ops={'created_at': 'DESC'}),
    )
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': str(self.id),
            'org_id': self.org_id,
            'actor_id': self.actor_id,
            'type': self.type,
            'severity': self.severity,
            'meta': self.meta,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def log_event(cls, db, org_id: str, event_type: str, severity: str, 
                  actor_id: str = None, meta: dict = None):
        """Log a risk event."""
        event = cls(
            org_id=org_id,
            actor_id=actor_id,
            type=event_type,
            severity=severity,
            meta=meta or {}
        )
        db.add(event)
        db.commit()
        return event
    
    @classmethod
    def get_recent_for_org(cls, db, org_id: str, days: int = 7):
        """Get recent risk events for an org."""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        return db.query(cls).filter(
            cls.org_id == org_id,
            cls.created_at >= cutoff
        ).order_by(cls.created_at.desc()).all()

