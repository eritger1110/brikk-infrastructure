# -*- coding: utf-8 -*-
"""
Usage Event model for tracking API usage, costs, and performance metrics.
Part of Phase 10-12: Production-ready billing and observability.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.infra.db import db


class UsageEvent(db.Model):
    """
    Usage event for tracking API calls, costs, and performance.
    Enables usage-based billing, budget enforcement, and analytics.
    """
    __tablename__ = "usage_events"

    # Identity
    id = Column(Integer, primary_key=True)
    request_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Ownership
    api_key_id = Column(
        Integer,
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    api_key = relationship("ApiKey", back_populates="usage_events")

    # Provider and model
    provider = Column(String(50), nullable=False, index=True)  # openai | mistral
    model = Column(String(100), nullable=False)

    # Token usage
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)

    # Cost tracking (server-side calculation)
    cost_usd = Column(Numeric(12, 6), nullable=False, default=Decimal('0'))

    # Performance
    latency_ms = Column(Integer, nullable=False, default=0)

    # Reliability
    fallback = Column(Boolean, nullable=False, default=False)
    error_message = Column(String(500))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_usage_key_created', 'api_key_id', 'created_at'),
        Index('idx_usage_provider_created', 'provider', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<UsageEvent {self.id} provider={self.provider} cost=${self.cost_usd}>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "request_id": str(self.request_id),
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
            "cost_usd": float(self.cost_usd),
            "latency_ms": self.latency_ms,
            "fallback": self.fallback,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def create_event(
        cls,
        request_id: str,
        api_key_id: int,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: Decimal,
        latency_ms: int,
        fallback: bool = False,
        error_message: str | None = None,
    ) -> "UsageEvent":
        """Create and persist a new usage event"""
        event = cls(
            request_id=request_id,
            api_key_id=api_key_id,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            fallback=fallback,
            error_message=error_message,
        )
        db.session.add(event)
        db.session.commit()
        return event

    @classmethod
    def get_usage_summary(
        cls,
        api_key_id: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """
        Get usage summary for an API key within a date range.
        Returns total cost, requests, tokens, and breakdown by provider.
        """
        from sqlalchemy import func

        query = cls.query.filter_by(api_key_id=api_key_id)

        if start_date:
            query = query.filter(cls.created_at >= start_date)
        if end_date:
            query = query.filter(cls.created_at <= end_date)

        # Overall totals
        totals = query.with_entities(
            func.count(cls.id).label('total_requests'),
            func.sum(cls.cost_usd).label('total_cost'),
            func.sum(cls.prompt_tokens).label('total_prompt_tokens'),
            func.sum(cls.completion_tokens).label('total_completion_tokens'),
            func.avg(cls.latency_ms).label('avg_latency_ms'),
            func.sum(func.cast(cls.fallback, Integer)).label('fallback_count'),
        ).first()

        # Breakdown by provider
        by_provider = query.with_entities(
            cls.provider,
            func.count(cls.id).label('requests'),
            func.sum(cls.cost_usd).label('cost'),
            func.avg(cls.latency_ms).label('avg_latency'),
        ).group_by(cls.provider).all()

        return {
            "total_requests": totals.total_requests or 0,
            "total_cost_usd": float(totals.total_cost or 0),
            "total_tokens": (totals.total_prompt_tokens or 0) + (totals.total_completion_tokens or 0),
            "avg_latency_ms": int(totals.avg_latency_ms or 0),
            "fallback_count": totals.fallback_count or 0,
            "by_provider": [
                {
                    "provider": p.provider,
                    "requests": p.requests,
                    "cost_usd": float(p.cost),
                    "avg_latency_ms": int(p.avg_latency),
                }
                for p in by_provider
            ],
        }

