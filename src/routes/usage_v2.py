# -*- coding: utf-8 -*-
"""
Usage tracking endpoints (API Key based)
Part of Phase 10-12: Production-ready billing
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta

from src.middleware.auth_middleware import require_api_key, get_current_api_key, get_current_api_key_id
from src.services.usage_metering_service import UsageMeteringService
from src.models.usage_event import UsageEvent

usage_v2_bp = Blueprint('usage_v2', __name__, url_prefix='/v2/usage')


@usage_v2_bp.route('/me', methods=['GET'])
@require_api_key
def get_my_usage():
    """
    Get usage summary for the current API key.
    
    Returns today, this week, this month, and recent events.
    """
    api_key = get_current_api_key()
    api_key_id = get_current_api_key_id()

    if not api_key_id:
        return jsonify({"error": "Authentication required"}), 401

    # Get usage for different time periods
    usage_today = UsageMeteringService.get_usage_today(api_key_id)
    usage_week = UsageMeteringService.get_usage_this_week(api_key_id)
    usage_month = UsageMeteringService.get_usage_this_month(api_key_id)

    # Get detailed summary for today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_summary = UsageMeteringService.get_usage_summary(api_key_id, start_date=today_start)

    # Get recent events
    recent_events = UsageMeteringService.get_recent_events(api_key_id, limit=10)

    return jsonify({
        "api_key_id": api_key_id,
        "api_key_prefix": api_key.key_prefix if api_key else None,
        "plan": api_key.name if api_key else "unknown",
        "today": {
            "cost_usd": float(usage_today),
            "requests": today_summary['total_requests'],
            "tokens": today_summary['total_tokens'],
            "avg_latency_ms": today_summary['avg_latency_ms'],
            "by_provider": today_summary['by_provider'],
        },
        "this_week": {
            "cost_usd": float(usage_week),
        },
        "this_month": {
            "cost_usd": float(usage_month),
        },
        "limits": {
            "soft_cap_usd": float(api_key.soft_cap_usd) if api_key and api_key.soft_cap_usd else 5.00,
            "hard_cap_usd": float(api_key.hard_cap_usd) if api_key and api_key.hard_cap_usd else 10.00,
            "rate_limit_per_min": api_key.requests_per_minute if api_key else 60,
        },
        "status": {
            "soft_cap_exceeded": usage_today >= (api_key.soft_cap_usd if api_key and api_key.soft_cap_usd else 5.00),
            "hard_cap_exceeded": usage_today >= (api_key.hard_cap_usd if api_key and api_key.hard_cap_usd else 10.00),
        },
        "recent_events": [event.to_dict() for event in recent_events],
    }), 200

