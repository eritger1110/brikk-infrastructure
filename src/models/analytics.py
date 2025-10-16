"""
Analytics models for Phase 7
Handles agent usage tracking, performance metrics, and aggregated analytics
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, date
from typing import Optional, Dict, Any
from decimal import Decimal

from src.infra.db import db
from src.models.agent import JSONDict


class AgentUsageEvent(db.Model):
    """
    Individual agent usage events for detailed tracking
    High-volume table - consider partitioning in production
    """
    __tablename__ = 'agent_usage_events'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = db.Column(db.String(36), db.ForeignKey('agents.id'), nullable=False)
    user_id = db.Column(db.String(36))  # Nullable for anonymous usage
    
    # Event details
    event_type = db.Column(db.String(50), nullable=False)  # invocation, error, timeout, etc.
    duration_ms = db.Column(db.Integer)
    success = db.Column(db.Boolean)
    error_message = db.Column(db.Text)
    
    # Flexible metadata storage
    event_metadata = db.Column(JSONDict)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationships
    agent = db.relationship('Agent', backref='usage_events', lazy=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'user_id': self.user_id,
            'event_type': self.event_type,
            'duration_ms': self.duration_ms,
            'success': self.success,
            'error_message': self.error_message,
            'metadata': self.event_metadata or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AgentAnalyticsDaily(db.Model):
    """
    Pre-computed daily analytics for agents
    Aggregated from usage events for performance
    """
    __tablename__ = 'agent_analytics_daily'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = db.Column(db.String(36), db.ForeignKey('agents.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    
    # Volume metrics
    invocation_count = db.Column(db.Integer, default=0)
    unique_users = db.Column(db.Integer, default=0)
    success_count = db.Column(db.Integer, default=0)
    error_count = db.Column(db.Integer, default=0)
    
    # Performance metrics
    avg_duration_ms = db.Column(db.Numeric(10, 2))
    p50_duration_ms = db.Column(db.Integer)  # Median
    p95_duration_ms = db.Column(db.Integer)
    p99_duration_ms = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Unique constraint: one record per agent per day
    __table_args__ = (
        db.UniqueConstraint('agent_id', 'date', name='uq_agent_analytics_daily'),
    )
    
    # Relationships
    agent = db.relationship('Agent', backref='daily_analytics', lazy=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analytics to dictionary"""
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'date': self.date.isoformat() if self.date else None,
            'invocation_count': self.invocation_count,
            'unique_users': self.unique_users,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': self.success_rate,
            'error_rate': self.error_rate,
            'avg_duration_ms': float(self.avg_duration_ms) if self.avg_duration_ms else None,
            'p50_duration_ms': self.p50_duration_ms,
            'p95_duration_ms': self.p95_duration_ms,
            'p99_duration_ms': self.p99_duration_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.invocation_count or 0
        if total == 0:
            return 0.0
        return (self.success_count or 0) / total
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate"""
        total = self.invocation_count or 0
        if total == 0:
            return 0.0
        return (self.error_count or 0) / total


class UserAnalyticsDaily(db.Model):
    """
    Pre-computed daily analytics for users
    Tracks user engagement and activity
    """
    __tablename__ = 'user_analytics_daily'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), nullable=False)
    date = db.Column(db.Date, nullable=False)
    
    # Activity metrics
    agents_used = db.Column(db.Integer, default=0)
    total_invocations = db.Column(db.Integer, default=0)
    active_time_minutes = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Unique constraint: one record per user per day
    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='uq_user_analytics_daily'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analytics to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.date.isoformat() if self.date else None,
            'agents_used': self.agents_used,
            'total_invocations': self.total_invocations,
            'active_time_minutes': self.active_time_minutes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AgentTrendingScore(db.Model):
    """
    Trending scores for agents
    Calculated periodically based on recent activity
    """
    __tablename__ = 'agent_trending_scores'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = db.Column(db.String(36), db.ForeignKey('agents.id'), nullable=False, unique=True)
    
    # Trending metrics
    trending_score = db.Column(db.Numeric(10, 4), default=0.0)  # Composite score
    velocity = db.Column(db.Numeric(10, 4), default=0.0)  # Rate of growth
    momentum = db.Column(db.Numeric(10, 4), default=0.0)  # Sustained growth
    
    # Contributing factors
    recent_installs = db.Column(db.Integer, default=0)
    recent_views = db.Column(db.Integer, default=0)
    recent_reviews = db.Column(db.Integer, default=0)
    recent_usage = db.Column(db.Integer, default=0)
    
    # Timestamps
    calculated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    agent = db.relationship('Agent', backref='trending_score', lazy=True, uselist=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trending score to dictionary"""
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'trending_score': float(self.trending_score) if self.trending_score else 0.0,
            'velocity': float(self.velocity) if self.velocity else 0.0,
            'momentum': float(self.momentum) if self.momentum else 0.0,
            'recent_installs': self.recent_installs,
            'recent_views': self.recent_views,
            'recent_reviews': self.recent_reviews,
            'recent_usage': self.recent_usage,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def calculate_score(self):
        """
        Calculate trending score based on multiple factors
        Higher weight for recent activity, installs, and sustained growth
        """
        # Weighted components
        install_weight = 3.0
        view_weight = 1.0
        review_weight = 2.0
        usage_weight = 2.5
        
        # Calculate base score
        base_score = (
            (self.recent_installs or 0) * install_weight +
            (self.recent_views or 0) * view_weight +
            (self.recent_reviews or 0) * review_weight +
            (self.recent_usage or 0) * usage_weight
        )
        
        # Apply velocity and momentum multipliers
        velocity_multiplier = 1.0 + (self.velocity or 0)
        momentum_multiplier = 1.0 + (self.momentum or 0)
        
        self.trending_score = base_score * velocity_multiplier * momentum_multiplier
        self.updated_at = datetime.now(timezone.utc)
        db.session.commit()

