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

# Tier-based rate limits (requests per minute)
RATE_LIMITS = {
    'FREE': '60/minute',
    'PRO': '600/minute',
    'ENT': '10000/minute',  # Enterprise tier
    'INTERNAL': '10000/minute',  # HMAC/internal use
    'DEFAULT': '60/minute'  # Unauthenticated requests
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
        Rate limit string (e.g., "60/minute", "600/minute")
    """
    if hasattr(g, 'tier'):
        tier = g.tier
        return RATE_LIMITS.get(tier, RATE_LIMITS['DEFAULT'])
    
    # Unauthenticated requests get default limit
    return RATE_LIMITS['DEFAULT']


def rate_limit_exceeded_handler(e):
    """
    Custom handler for rate limit exceeded errors.
    
    Returns JSON response with rate limit information.
    """
    return jsonify({
        'error': 'rate_limit_exceeded',
        'message': 'Rate limit exceeded. Please try again later.',
        'retry_after': e.description,
        'limit': get_rate_limit(),
        'tier': getattr(g, 'tier', 'DEFAULT')
    }), 429


def init_rate_limiter(app):
    """
    Initialize Flask-Limiter with the app.
    
    Args:
        app: Flask application instance
    
    Returns:
        Configured Limiter instance
    """
    limiter = Limiter(
        app=app,
        key_func=get_actor_identifier,
        default_limits=[get_rate_limit],
        storage_uri="redis://localhost:6379",  # Use Redis for distributed limiting
        storage_options={"socket_connect_timeout": 30},
        strategy="fixed-window",
        headers_enabled=True,  # Add X-RateLimit-* headers
        on_breach=rate_limit_exceeded_handler
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

