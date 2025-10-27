# -*- coding: utf-8 -*-
"""
Usage metering service for Brikk API
Records usage events and tracks costs
Part of Phase 10-12: Production-ready billing
"""

import uuid
from decimal import Decimal
from datetime import datetime

from src.models.usage_event import UsageEvent
from src.services.cost_service import calc_cost
from src.infra.db import db


class UsageMeteringService:
    """Service for recording and tracking API usage"""

    @staticmethod
    def record_usage(
        api_key_id: int,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        fallback: bool = False,
        error_message: str | None = None,
        request_id: str | None = None,
    ) -> UsageEvent:
        """
        Record a usage event and calculate cost.
        
        Args:
            api_key_id: API key ID
            provider: Provider name (openai, mistral)
            model: Model name
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            latency_ms: Request latency in milliseconds
            fallback: Whether fallback was used
            error_message: Error message if request failed
            request_id: Request ID (generated if not provided)
        
        Returns:
            Created UsageEvent record
        """
        # Generate request ID if not provided
        if not request_id:
            request_id = str(uuid.uuid4())

        # Calculate cost
        cost_usd = calc_cost(provider, model, prompt_tokens, completion_tokens)

        # Create usage event
        event = UsageEvent.create_event(
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

        return event

    @staticmethod
    def get_usage_summary(
        api_key_id: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """
        Get usage summary for an API key.
        
        Args:
            api_key_id: API key ID
            start_date: Start date for summary (optional)
            end_date: End date for summary (optional)
        
        Returns:
            Usage summary dict
        """
        return UsageEvent.get_usage_summary(api_key_id, start_date, end_date)

    @staticmethod
    def get_usage_today(api_key_id: int) -> Decimal:
        """
        Get total cost for API key today.
        
        Args:
            api_key_id: API key ID
        
        Returns:
            Total cost in USD
        """
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        total = db.session.query(db.func.sum(UsageEvent.cost_usd)).filter(
            UsageEvent.api_key_id == api_key_id,
            UsageEvent.created_at >= today_start
        ).scalar()

        return total or Decimal('0')

    @staticmethod
    def get_usage_this_week(api_key_id: int) -> Decimal:
        """Get total cost for API key this week"""
        from datetime import timedelta
        week_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)

        total = db.session.query(db.func.sum(UsageEvent.cost_usd)).filter(
            UsageEvent.api_key_id == api_key_id,
            UsageEvent.created_at >= week_start
        ).scalar()

        return total or Decimal('0')

    @staticmethod
    def get_usage_this_month(api_key_id: int) -> Decimal:
        """Get total cost for API key this month"""
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total = db.session.query(db.func.sum(UsageEvent.cost_usd)).filter(
            UsageEvent.api_key_id == api_key_id,
            UsageEvent.created_at >= month_start
        ).scalar()

        return total or Decimal('0')

    @staticmethod
    def get_recent_events(api_key_id: int, limit: int = 10) -> list[UsageEvent]:
        """
        Get recent usage events for an API key.
        
        Args:
            api_key_id: API key ID
            limit: Maximum number of events to return
        
        Returns:
            List of UsageEvent records
        """
        return UsageEvent.query.filter_by(api_key_id=api_key_id).order_by(
            UsageEvent.created_at.desc()
        ).limit(limit).all()

