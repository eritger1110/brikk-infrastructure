# -*- coding: utf-8 -*-
"""
Audit Logging Service for API Gateway.

Logs all API requests to the api_audit_log table for compliance and debugging.
Includes request details, authentication info, and response status.
"""
import time
import uuid
from datetime import datetime
from flask import g, request, current_app
from src.database import db
from src.models.api_gateway import ApiAuditLog


def log_api_request(response_status: int, response_time_ms: float):
    """
    Log an API request to the audit log.
    
    Args:
        response_status: HTTP response status code
        response_time_ms: Request processing time in milliseconds
    
    This should be called after the request is processed.
    """
    try:
        # Generate request ID if not already set
        request_id = getattr(g, 'request_id', str(uuid.uuid4()))
        
        # Extract authentication details
        org_id = getattr(g, 'org_id', None)
        actor_id = getattr(g, 'actor_id', None)
        actor_type = getattr(g, 'actor_type', 'anon')  # api_key|oauth|hmac|anon
        auth_method = getattr(g, 'auth_method', 'api_key')
        
        # Skip if missing required fields
        if not org_id or not actor_id:
            return
        
        # Create audit log entry with correct field names
        audit_entry = ApiAuditLog(
            request_id=request_id,
            org_id=org_id,
            actor_type=actor_type,
            actor_id=actor_id,
            auth_method=auth_method,
            method=request.method,
            path=request.path,
            status=response_status,
            cost_units=0,  # Will be updated by usage metering
            ip=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.add(audit_entry)
        db.session.commit()
        
    except Exception as e:
        # Don't fail the request if audit logging fails
        current_app.logger.error(f"Audit logging failed: {e}")
        db.session.rollback()


def init_audit_logging(app):
    """
    Initialize audit logging middleware.
    
    Args:
        app: Flask application instance
    """
    # Note: request_id and request_start_time are set by RequestContextMiddleware
    # We don't need to set them here to avoid conflicts
    
    @app.after_request
    def after_request(response):
        """Log the request after processing."""
        if hasattr(g, 'request_start_time'):
            # Calculate response time (request_start_time is a float from time.time())
            response_time = (time.time() - g.request_start_time) * 1000
            
            # Log to audit table
            log_api_request(response.status_code, response_time)
        
        return response

