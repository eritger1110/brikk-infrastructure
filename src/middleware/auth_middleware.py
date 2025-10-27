# -*- coding: utf-8 -*-
"""
Authentication middleware for Brikk API
Handles API key validation, rate limiting, and budget enforcement
Part of Phase 10-12: Production-ready security
"""

import os
import time
from functools import wraps
from flask import request, jsonify, g
from datetime import datetime, timedelta
from decimal import Decimal

from src.models.api_key import ApiKey
from src.models.usage_event import UsageEvent
from src.infra.db import db


# Configuration from environment
REQUIRE_AUTH = os.getenv('BRIKK_REQUIRE_AUTH', 'false').lower() == 'true'
DEFAULT_SOFT_CAP = Decimal(os.getenv('BRIKK_DEFAULT_SOFT_CAP_USD', '5.00'))
DEFAULT_HARD_CAP = Decimal(os.getenv('BRIKK_DEFAULT_HARD_CAP_USD', '10.00'))
DEFAULT_RATE_LIMIT = int(os.getenv('BRIKK_RATE_LIMIT_PER_MIN', '60'))


# In-memory rate limit tracking (simple implementation)
# In production, use Redis for distributed rate limiting
_rate_limit_cache = {}


def clean_rate_limit_cache():
    """Clean expired entries from rate limit cache"""
    now = time.time()
    expired_keys = [k for k, v in _rate_limit_cache.items() if v['reset_at'] < now]
    for k in expired_keys:
        del _rate_limit_cache[k]


def check_rate_limit(api_key_id: int, limit_per_min: int) -> tuple[bool, dict]:
    """
    Check if request is within rate limit.
    Returns (allowed: bool, headers: dict)
    """
    clean_rate_limit_cache()

    now = time.time()
    key = f"ratelimit:{api_key_id}"

    if key not in _rate_limit_cache:
        _rate_limit_cache[key] = {
            'count': 0,
            'reset_at': now + 60  # 1 minute window
        }

    cache_entry = _rate_limit_cache[key]

    # Reset if window expired
    if now >= cache_entry['reset_at']:
        cache_entry['count'] = 0
        cache_entry['reset_at'] = now + 60

    # Check limit
    if cache_entry['count'] >= limit_per_min:
        headers = {
            'X-RateLimit-Limit': str(limit_per_min),
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': str(int(cache_entry['reset_at'])),
        }
        return False, headers

    # Increment counter
    cache_entry['count'] += 1

    headers = {
        'X-RateLimit-Limit': str(limit_per_min),
        'X-RateLimit-Remaining': str(limit_per_min - cache_entry['count']),
        'X-RateLimit-Reset': str(int(cache_entry['reset_at'])),
    }

    return True, headers


def get_usage_today(api_key_id: int) -> Decimal:
    """Get total cost for API key today"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total = db.session.query(db.func.sum(UsageEvent.cost_usd)).filter(
        UsageEvent.api_key_id == api_key_id,
        UsageEvent.created_at >= today_start
    ).scalar()

    return total or Decimal('0')


def check_budget(api_key: ApiKey) -> tuple[bool, bool, dict]:
    """
    Check if API key is within budget.
    Returns (allowed: bool, soft_cap_exceeded: bool, headers: dict)
    """
    usage_today = get_usage_today(api_key.id)

    soft_cap = api_key.soft_cap_usd or DEFAULT_SOFT_CAP
    hard_cap = api_key.hard_cap_usd or DEFAULT_HARD_CAP

    headers = {
        'X-Brikk-Usage-Today': str(float(usage_today)),
        'X-Brikk-Soft-Cap': str(float(soft_cap)),
        'X-Brikk-Hard-Cap': str(float(hard_cap)),
    }

    # Hard cap exceeded - block request
    if usage_today >= hard_cap:
        headers['X-Brikk-Hard-Cap-Exceeded'] = 'true'
        return False, True, headers

    # Soft cap exceeded - allow but warn
    if usage_today >= soft_cap:
        headers['X-Brikk-Soft-Cap-Exceeded'] = 'true'
        return True, True, headers

    return True, False, headers


def require_api_key(f):
    """
    Decorator to require API key authentication on routes.
    Also enforces rate limiting and budget caps.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if auth is required
        if not REQUIRE_AUTH:
            # Auth disabled - allow request but set placeholder
            g.api_key = None
            g.api_key_id = None
            return f(*args, **kwargs)

        # Extract API key from header
        api_key_header = request.headers.get('X-Brikk-API-Key')

        if not api_key_header:
            return jsonify({
                "error": "Missing API key",
                "message": "Include X-Brikk-API-Key header with your request",
                "docs": "https://api.getbrikk.com/docs"
            }), 401

        # Authenticate API key
        api_key_record = ApiKey.authenticate_api_key(api_key_header)

        if not api_key_record:
            return jsonify({
                "error": "Invalid API key",
                "message": "The provided API key is invalid or expired",
                "docs": "https://api.getbrikk.com/docs"
            }), 401

        # Check if key is active and valid
        if not api_key_record.is_valid():
            return jsonify({
                "error": "API key expired or disabled",
                "message": "Your API key has expired or been disabled",
                "docs": "https://api.getbrikk.com/docs"
            }), 401

        # Check rate limit
        rate_limit = api_key_record.requests_per_minute or DEFAULT_RATE_LIMIT
        allowed, rate_headers = check_rate_limit(api_key_record.id, rate_limit)

        if not allowed:
            response = jsonify({
                "error": "Rate limit exceeded",
                "message": f"You have exceeded the rate limit of {rate_limit} requests per minute",
                "retry_after": int(rate_headers['X-RateLimit-Reset']) - int(time.time())
            })
            for k, v in rate_headers.items():
                response.headers[k] = v
            return response, 429

        # Check budget
        allowed, soft_cap_exceeded, budget_headers = check_budget(api_key_record)

        if not allowed:
            response = jsonify({
                "error": "Budget exceeded",
                "message": f"You have exceeded your daily budget cap of ${budget_headers['X-Brikk-Hard-Cap']}",
                "usage_today": budget_headers['X-Brikk-Usage-Today']
            })
            for k, v in budget_headers.items():
                response.headers[k] = v
            return response, 429

        # Store API key in Flask's g object for use in route
        g.api_key = api_key_record
        g.api_key_id = api_key_record.id
        g.soft_cap_exceeded = soft_cap_exceeded

        # Call the actual route function
        response = f(*args, **kwargs)

        # Add rate limit and budget headers to response
        if isinstance(response, tuple):
            response_obj, status_code = response[0], response[1]
        else:
            response_obj, status_code = response, 200

        for k, v in rate_headers.items():
            response_obj.headers[k] = v
        for k, v in budget_headers.items():
            response_obj.headers[k] = v

        return response_obj, status_code

    return decorated_function


def get_current_api_key() -> ApiKey | None:
    """Get the current API key from Flask's g object"""
    return getattr(g, 'api_key', None)


def get_current_api_key_id() -> int | None:
    """Get the current API key ID from Flask's g object"""
    return getattr(g, 'api_key_id', None)


def is_soft_cap_exceeded() -> bool:
    """Check if soft cap has been exceeded for current request"""
    return getattr(g, 'soft_cap_exceeded', False)

