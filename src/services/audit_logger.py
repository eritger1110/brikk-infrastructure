# -*- coding: utf-8 -*-
"""
Audit Logging Service for API Gateway.

Logs all API requests to the api_audit_log table for compliance and debugging.
Includes request details, authentication info, and response status.
"""
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
        auth_method = getattr(g, 'auth_method', None)
        
        # Create audit log entry
        audit_entry = ApiAuditLog(
            request_id=request_id,
            org_id=org_id,
            actor_id=actor_id,
            auth_method=auth_method,
            endpoint=request.endpoint,
            method=request.method,
            path=request.path,
            query_params=dict(request.args) if request.args else None,
            request_ip=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            response_status=response_status,
            response_time_ms=response_time_ms
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
    @app.before_request
    def before_request():
        """Set up request tracking."""
        g.request_id = str(uuid.uuid4())
        g.request_start_time = datetime.utcnow()
    
    @app.after_request
    def after_request(response):
        """Log the request after processing."""
        if hasattr(g, 'request_start_time'):
            # Calculate response time
            response_time = (datetime.utcnow() - g.request_start_time).total_seconds() * 1000
            
            # Log to audit table
            log_api_request(response.status_code, response_time)
            
            # Add request ID to response headers
            response.headers['X-Request-ID'] = g.request_id
        
        return response

