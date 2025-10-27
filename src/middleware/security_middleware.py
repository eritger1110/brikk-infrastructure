# -*- coding: utf-8 -*-
"""
Security middleware for production hardening
Part of Phase 10-12: Production-ready security
"""

from flask import request, g
from functools import wraps
import logging
import os

from src.models.audit_log import AuditLog
from src.infra.db import db

logger = logging.getLogger(__name__)


def add_security_headers(response):
    """
    Add security headers to all responses.
    
    Headers added:
    - Strict-Transport-Security (HSTS)
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Referrer-Policy
    """
    # HSTS: Force HTTPS for 1 year
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    
    # XSS protection (legacy, but still good to have)
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Permissions policy (restrict features)
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    return response


def log_audit_event(
    event_type,
    api_key_id=None,
    resource_type=None,
    resource_id=None,
    details=None,
    ip_address=None,
    user_agent=None
):
    """
    Log an audit event to the database.
    
    Args:
        event_type: Type of event (e.g., 'api_call', 'key_rotation', 'auth_failure')
        api_key_id: ID of the API key (if applicable)
        resource_type: Type of resource accessed (e.g., 'agent', 'usage')
        resource_id: ID of the resource
        details: Additional details (JSON)
        ip_address: Client IP address
        user_agent: Client user agent
    """
    try:
        audit_log = AuditLog(
            event_type=event_type,
            api_key_id=api_key_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address or request.remote_addr,
            user_agent=user_agent or request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        logger.info(f"Audit log created: {event_type}", extra={
            "event_type": event_type,
            "api_key_id": api_key_id,
            "resource_type": resource_type,
            "ip_address": ip_address or request.remote_addr
        })
    except Exception as e:
        logger.error(f"Failed to create audit log: {str(e)}", exc_info=True)
        # Don't fail the request if audit logging fails
        db.session.rollback()


def audit_api_call(f):
    """
    Decorator to audit API calls.
    
    Logs all authenticated API calls with request details.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Execute the function first
        response = f(*args, **kwargs)
        
        # Log the API call
        api_key_id = getattr(g, 'api_key_id', None)
        
        if api_key_id:
            # Determine resource type from endpoint
            resource_type = None
            if '/agents/' in request.path:
                resource_type = 'agent'
            elif '/usage/' in request.path:
                resource_type = 'usage'
            elif '/keys/' in request.path:
                resource_type = 'key'
            
            # Get status code
            status_code = response.status_code if hasattr(response, 'status_code') else 200
            
            log_audit_event(
                event_type='api_call',
                api_key_id=api_key_id,
                resource_type=resource_type,
                details={
                    'method': request.method,
                    'path': request.path,
                    'status_code': status_code,
                    'request_id': getattr(g, 'request_id', None)
                }
            )
        
        return response
    
    return decorated_function


def check_cors_allowlist():
    """
    Check if the request origin is in the CORS allowlist.
    
    In production, only allow specific origins.
    """
    origin = request.headers.get('Origin')
    
    if not origin:
        return True  # No origin header, allow
    
    # Get allowed origins from environment
    allowed_origins_str = os.getenv('CORS_ALLOWED_ORIGINS', '')
    
    if not allowed_origins_str:
        # If no allowlist configured, allow all (dev mode)
        return True
    
    allowed_origins = [o.strip() for o in allowed_origins_str.split(',')]
    
    if origin in allowed_origins:
        return True
    
    logger.warning(f"CORS violation: {origin} not in allowlist", extra={
        "origin": origin,
        "allowed_origins": allowed_origins
    })
    
    return False


def init_security_middleware(app):
    """
    Initialize security middleware for the Flask app.
    
    Args:
        app: Flask application instance
    """
    # Add security headers to all responses
    @app.after_request
    def apply_security_headers(response):
        return add_security_headers(response)
    
    logger.info("Security middleware initialized")

