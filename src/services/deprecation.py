# -*- coding: utf-8 -*-
"""
API Deprecation Warnings Framework (Phase 6 PR-M).

Provides decorators and utilities for managing API deprecation gracefully.
"""
from functools import wraps
from flask import g, request, jsonify
from datetime import datetime, timedelta
from typing import Optional, Callable
import warnings

# Deprecation registry
DEPRECATED_ENDPOINTS = {}


class DeprecationWarning:
    """Represents a deprecation warning for an API endpoint or feature."""
    
    def __init__(
        self,
        endpoint: str,
        deprecated_since: str,
        sunset_date: Optional[str] = None,
        replacement: Optional[str] = None,
        message: Optional[str] = None
    ):
        """
        Initialize deprecation warning.
        
        Args:
            endpoint: The deprecated endpoint path
            deprecated_since: ISO date when deprecation started (e.g., "2025-10-16")
            sunset_date: ISO date when endpoint will be removed (optional)
            replacement: Suggested replacement endpoint (optional)
            message: Custom deprecation message (optional)
        """
        self.endpoint = endpoint
        self.deprecated_since = deprecated_since
        self.sunset_date = sunset_date
        self.replacement = replacement
        self.message = message or f"Endpoint {endpoint} is deprecated"
    
    def to_headers(self) -> dict:
        """Convert to HTTP headers."""
        headers = {
            'X-API-Deprecated': 'true',
            'X-API-Deprecated-Since': self.deprecated_since,
        }
        
        if self.sunset_date:
            headers['X-API-Sunset-Date'] = self.sunset_date
            headers['Sunset'] = self.sunset_date  # RFC 8594
        
        if self.replacement:
            headers['X-API-Replacement'] = self.replacement
        
        return headers
    
    def to_warning_header(self) -> str:
        """
        Convert to Warning header (RFC 7234).
        
        Format: Warning: 299 - "message" "date"
        """
        warning_msg = self.message
        if self.sunset_date:
            warning_msg += f" and will be removed on {self.sunset_date}"
        if self.replacement:
            warning_msg += f". Use {self.replacement} instead"
        
        return f'299 - "{warning_msg}" "{self.deprecated_since}"'


def deprecated(
    since: str,
    sunset: Optional[str] = None,
    replacement: Optional[str] = None,
    message: Optional[str] = None
):
    """
    Decorator to mark an endpoint as deprecated.
    
    Usage:
        @app.route('/old-endpoint')
        @deprecated(since='2025-10-16', sunset='2026-01-01', replacement='/v2/new-endpoint')
        def old_endpoint():
            return {'data': 'value'}
    
    Args:
        since: ISO date when deprecation started
        sunset: ISO date when endpoint will be removed (optional)
        replacement: Suggested replacement endpoint (optional)
        message: Custom deprecation message (optional)
    """
    def decorator(f: Callable) -> Callable:
        # Register deprecation
        endpoint_path = f.__name__
        deprecation = DeprecationWarning(
            endpoint=endpoint_path,
            deprecated_since=since,
            sunset_date=sunset,
            replacement=replacement,
            message=message
        )
        DEPRECATED_ENDPOINTS[endpoint_path] = deprecation
        
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Execute the original function
            response = f(*args, **kwargs)
            
            # If response is a tuple (body, status, headers)
            if isinstance(response, tuple):
                body, status = response[0], response[1]
                headers = response[2] if len(response) > 2 else {}
            else:
                body, status, headers = response, 200, {}
            
            # Add deprecation headers
            deprecation_headers = deprecation.to_headers()
            deprecation_headers['Warning'] = deprecation.to_warning_header()
            
            # Merge headers
            if isinstance(headers, dict):
                headers.update(deprecation_headers)
            else:
                headers = deprecation_headers
            
            return body, status, headers
        
        return wrapper
    return decorator


def check_deprecated_features(response):
    """
    After-request handler to check for deprecated features.
    
    This can be registered as an after_request handler to add
    deprecation warnings based on request patterns.
    """
    # Check if endpoint is deprecated
    endpoint = request.endpoint
    if endpoint and endpoint in DEPRECATED_ENDPOINTS:
        deprecation = DEPRECATED_ENDPOINTS[endpoint]
        
        # Add deprecation headers
        for key, value in deprecation.to_headers().items():
            response.headers[key] = value
        
        response.headers['Warning'] = deprecation.to_warning_header()
    
    return response


def get_deprecations() -> dict:
    """Get all registered deprecations."""
    return {
        endpoint: {
            'deprecated_since': dep.deprecated_since,
            'sunset_date': dep.sunset_date,
            'replacement': dep.replacement,
            'message': dep.message
        }
        for endpoint, dep in DEPRECATED_ENDPOINTS.items()
    }


def is_deprecated(endpoint: str) -> bool:
    """Check if an endpoint is deprecated."""
    return endpoint in DEPRECATED_ENDPOINTS


def days_until_sunset(endpoint: str) -> Optional[int]:
    """Calculate days until sunset for a deprecated endpoint."""
    if endpoint not in DEPRECATED_ENDPOINTS:
        return None
    
    deprecation = DEPRECATED_ENDPOINTS[endpoint]
    if not deprecation.sunset_date:
        return None
    
    try:
        sunset = datetime.fromisoformat(deprecation.sunset_date)
        now = datetime.now()
        delta = sunset - now
        return max(0, delta.days)
    except (ValueError, TypeError):
        return None

