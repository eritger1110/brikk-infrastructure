# -*- coding: utf-8 -*-
"""
Request/Response Size Limit Middleware (Phase 6 PR-L).

Enforces size limits on requests and responses to prevent abuse and ensure system stability.
"""
from flask import Flask, request, g, jsonify
from werkzeug.exceptions import RequestEntityTooLarge
from typing import Optional

# Size limits in bytes
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10 MB default
MAX_RESPONSE_SIZE = 50 * 1024 * 1024  # 50 MB default

# Tier-specific request size limits
TIER_REQUEST_LIMITS = {
    'FREE': 1 * 1024 * 1024,      # 1 MB
    'HACKER': 5 * 1024 * 1024,    # 5 MB
    'STARTER': 10 * 1024 * 1024,  # 10 MB
    'PRO': 25 * 1024 * 1024,      # 25 MB
    'ENT': 100 * 1024 * 1024,     # 100 MB
    'INTERNAL': 100 * 1024 * 1024,  # 100 MB
    'DEFAULT': 1 * 1024 * 1024    # 1 MB for unauthenticated
}


class SizeLimitMiddleware:
    """Middleware for enforcing request/response size limits."""
    
    def __init__(self, app: Optional[Flask] = None):
        """Initialize middleware."""
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize middleware with Flask app."""
        # Register before_request handler
        app.before_request(self._check_request_size)
        
        # Register after_request handler
        app.after_request(self._check_response_size)
        
        # Register error handler for request entity too large
        app.errorhandler(RequestEntityTooLarge)(self._handle_request_too_large)
        app.errorhandler(413)(self._handle_request_too_large)
    
    def _check_request_size(self):
        """Check request size before processing."""
        # Get content length from headers
        content_length = request.content_length
        
        if content_length is None:
            # No content length header, skip check
            return None
        
        # Get tier-specific limit
        tier = getattr(g, 'tier', 'DEFAULT')
        max_size = TIER_REQUEST_LIMITS.get(tier, TIER_REQUEST_LIMITS['DEFAULT'])
        
        # Check if request exceeds limit
        if content_length > max_size:
            return jsonify({
                'error': 'request_too_large',
                'message': f'Request body exceeds maximum size of {max_size // (1024 * 1024)} MB for {tier} tier',
                'request_id': getattr(g, 'request_id', None),
                'max_size_bytes': max_size,
                'request_size_bytes': content_length,
                'tier': tier
            }), 413
        
        return None
    
    def _check_response_size(self, response):
        """Check response size after processing."""
        # Only check for successful responses with content
        if response.status_code >= 400:
            return response
        
        # Get response size
        if response.content_length:
            response_size = response.content_length
        elif response.data:
            response_size = len(response.data)
        else:
            return response
        
        # Check if response exceeds limit
        if response_size > MAX_RESPONSE_SIZE:
            # Log warning but don't block (response already generated)
            # In production, this should trigger monitoring alerts
            if hasattr(g, 'request_id'):
                print(f"WARNING: Response size ({response_size} bytes) exceeds limit for request {g.request_id}")
        
        # Add size header for debugging
        response.headers['X-Response-Size'] = str(response_size)
        
        return response
    
    def _handle_request_too_large(self, error):
        """Handle request entity too large errors."""
        tier = getattr(g, 'tier', 'DEFAULT')
        max_size = TIER_REQUEST_LIMITS.get(tier, TIER_REQUEST_LIMITS['DEFAULT'])
        
        return jsonify({
            'error': 'request_too_large',
            'message': f'Request body exceeds maximum size of {max_size // (1024 * 1024)} MB',
            'request_id': getattr(g, 'request_id', None),
            'max_size_bytes': max_size,
            'tier': tier
        }), 413


def get_max_request_size(tier: str = 'DEFAULT') -> int:
    """Get maximum request size for a tier."""
    return TIER_REQUEST_LIMITS.get(tier, TIER_REQUEST_LIMITS['DEFAULT'])

