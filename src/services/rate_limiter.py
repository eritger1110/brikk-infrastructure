# -*- coding: utf-8 -*-
"""
Rate Limiting Service for API Gateway.

Implements tiered rate limiting based on actor tier (FREE, PRO, ENT).
Uses Flask-Limiter with Redis backend for distributed rate limiting.
"""
from flask import g, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from typing import Optional

# Tier-based rate limits (PR-K: Expanded granular limits)
RATE_LIMITS = {
    # Free tier - Basic usage
    'FREE': {
        'minute': '60/minute',
        'hour': '1000/hour',
        'day': '10000/day'
    },
    # Hacker tier - For developers
    'HACKER': {
        'minute': '120/minute',
        'hour': '5000/hour',
        'day': '50000/day'
    },
    # Starter tier - Small teams
    'STARTER': {
        'minute': '300/minute',
        'hour': '15000/hour',
        'day': '200000/day'
    },
    # Pro tier - Growing businesses
    'PRO': {
        'minute': '600/minute',
        'hour': '30000/hour',
        'day': '500000/day'
    },
    # Enterprise tier - Large organizations
    'ENT': {
        'minute': '10000/minute',
        'hour': '500000/hour',
        'day': '10000000/day'
    },
    # Internal tier - HMAC/system-to-system
    'INTERNAL': {
        'minute': '10000/minute',
        'hour': '500000/hour',
        'day': '10000000/day'
    },
    # Default for unauthenticated
    'DEFAULT': {
        'minute': '60/minute',
        'hour': '500/hour',
        'day': '2000/day'
    }
}

# Legacy single-value limits for backward compatibility
LEGACY_RATE_LIMITS = {
    'FREE': '60/minute',
    'HACKER': '120/minute',
    'STARTER': '300/minute',
    'PRO': '600/minute',
    'ENT': '10000/minute',
    'INTERNAL': '10000/minute',
    'DEFAULT': '60/minute'
}


def get_actor_identifier() -> str:
    """
    Get unique identifier for rate limiting based on auth method.
    
    Returns:
        Unique identifier string for the current actor
        
    Priority:
        1. Authenticated actor (org_id + actor_id)
        2. IP address (for unauthenticated requests)
    """
    if hasattr(g, 'org_id') and hasattr(g, 'actor_id'):
        # Authenticated request - use org + actor
        return f"org:{g.org_id}:actor:{g.actor_id}"
    
    # Unauthenticated - use IP address
    return f"ip:{get_remote_address()}"


def get_rate_limit() -> str:
    """
    Get rate limit for current request based on actor tier.
    
    Returns:
        Rate limit string with multiple time windows (e.g., "60/minute;1000/hour;10000/day")
    """
    tier = getattr(g, 'tier', 'DEFAULT')
    limits = RATE_LIMITS.get(tier, RATE_LIMITS['DEFAULT'])
    
    # Return combined limits for multiple time windows
    if isinstance(limits, dict):
        return ';'.join([limits['minute'], limits['hour'], limits['day']])
    
    # Fallback to legacy format
    return LEGACY_RATE_LIMITS.get(tier, LEGACY_RATE_LIMITS['DEFAULT'])


def rate_limit_exceeded_handler(e):
    """
    Custom handler for rate limit exceeded errors.
    
    Returns JSON response with rate limit information.
    """
    # Get retry_after from the exception if available
    retry_after = getattr(e, 'description', None) or getattr(e, 'retry_after', 60)
    return jsonify({
        'error': 'rate_limit_exceeded',
        'message': 'Rate limit exceeded. Please try again later.',
        'retry_after': retry_after,
        'limit': get_rate_limit(),
        'tier': getattr(g, 'tier', 'DEFAULT')
    }), 429


def init_rate_limiter(app):
    """
    Initialize Flask-Limiter with the app.
    
    Gracefully falls back to in-memory storage if Redis is unavailable.
    
    Args:
        app: Flask application instance
    
    Returns:
        Configured Limiter instance
    """
    import os
    
    # Try Redis first, fall back to memory if unavailable
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    storage_uri = redis_url
    
    # Test Redis connection
    try:
        import redis
        r = redis.from_url(redis_url, socket_connect_timeout=2)
        r.ping()
        app.logger.info(f"Rate limiter using Redis: {redis_url}")
    except Exception as e:
        app.logger.warning(f"Redis unavailable ({e}), using in-memory storage for rate limiting")
        storage_uri = "memory://"  # Fall back to in-memory storage
    
    limiter = Limiter(
        app=app,
        key_func=get_actor_identifier,
        default_limits=[get_rate_limit],
        storage_uri=storage_uri,
        storage_options={"socket_connect_timeout": 2},
        strategy="fixed-window",
        headers_enabled=True,  # Add X-RateLimit-* headers
        on_breach=rate_limit_exceeded_handler,
        # Exempt health check endpoints from rate limiting
        default_limits_exempt_when=lambda: request.path in ['/health', '/healthz', '/readyz']
    )
    
    # Add rate limit headers to all responses
    @app.after_request
    def add_rate_limit_headers(response):
        """Add X-RateLimit-* headers to response."""
        if hasattr(g, 'view_rate_limit'):
            # Flask-Limiter automatically adds these headers
            pass
        else:
            # Add headers for non-limited routes
            limit = get_rate_limit()
            response.headers['X-RateLimit-Limit'] = limit.split('/')[0]
            response.headers['X-RateLimit-Tier'] = getattr(g, 'tier', 'DEFAULT')
        
        return response
    
    return limiter

