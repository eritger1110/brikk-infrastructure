# -*- coding: utf-8 -*-
"""
Request context middleware for Brikk coordination API.

Provides request_id generation and propagation throughout the request lifecycle:
- Generates unique request_id for each request
- Adds request_id to response headers
- Makes request_id available in Flask g context
- Supports request_id extraction from incoming headers
- Integrates with structured logging

Request IDs are UUIDs that help trace requests across logs and systems.
"""

import uuid
import time
from typing import Optional
from flask import Flask, request, g, Response


class RequestContextMiddleware:
    """Middleware for managing request context and request_id propagation."""

    def __init__(self, app: Flask):
        self.app = app

        # Register before_request and after_request handlers
        app.before_request(self._before_request)
        app.after_request(self._after_request)

    def _before_request(self):
        """Initialize request context before processing."""
        # Generate or extract request_id
        request_id = self._get_or_generate_request_id()

        # Store in Flask g context for access throughout request
        g.request_id = request_id
        g.request_start_time = time.time()

        # Store request metadata for logging
        g.request_method = request.method
        g.request_path = request.path
        g.request_remote_addr = request.remote_addr
        g.request_user_agent = request.headers.get('User-Agent', '')

        # Initialize auth context (will be populated by auth middleware)
        g.organization_id = None
        g.api_key_id = None
        g.auth_context = None

    def _after_request(self, response: Response) -> Response:
        """Add request context to response headers."""
        # Add request_id to response headers
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id

        # Add timing information for debugging
        if hasattr(g, 'request_start_time'):
            duration_ms = round((time.time() - g.request_start_time) * 1000, 2)
            response.headers['X-Response-Time'] = f"{duration_ms}ms"

        return response

    def _get_or_generate_request_id(self) -> str:
        """Get request_id from headers or generate new one."""
        # Check for existing request_id in headers
        request_id = request.headers.get('X-Request-ID')

        if request_id:
            # Validate that it looks like a UUID
            try:
                uuid.UUID(request_id)
                return request_id
            except ValueError:
                # Invalid UUID format, generate new one
                pass

        # Generate new request_id
        return str(uuid.uuid4())


def get_request_id() -> Optional[str]:
    """Get current request_id from Flask g context."""
    return getattr(g, 'request_id', None)


def get_request_context() -> dict:
    """Get complete request context for logging."""
    context = {
        'request_id': getattr(g, 'request_id', None),
        'method': getattr(g, 'request_method', None),
        'path': getattr(g, 'request_path', None),
        'remote_addr': getattr(g, 'request_remote_addr', None),
        'user_agent': getattr(g, 'request_user_agent', None),
    }

    # Add timing information if available
    if hasattr(g, 'request_start_time'):
        context['duration_ms'] = round(
            (time.time() - g.request_start_time) * 1000, 2)

    # Add auth context if available
    if hasattr(g, 'organization_id') and g.organization_id:
        context['organization_id'] = g.organization_id

    if hasattr(g, 'api_key_id') and g.api_key_id:
        context['api_key_id'] = g.api_key_id

    if hasattr(g, 'auth_context') and g.auth_context:
        context['auth_context'] = g.auth_context

    return context


def set_auth_context(organization_id: Optional[str] = None,
                     api_key_id: Optional[str] = None,
                     auth_context: Optional[dict] = None):
    """Set authentication context for current request."""
    if organization_id:
        g.organization_id = organization_id

    if api_key_id:
        g.api_key_id = api_key_id

    if auth_context:
        g.auth_context = auth_context


def init_request_context(app: Flask):
    """Initialize request context middleware for Flask application."""
    return RequestContextMiddleware(app)
