"""
Structured JSON logging service for Brikk coordination API.

Provides structured logging with:
- JSON format output when enabled
- Request context integration (request_id, auth info)
- Consistent log structure across the application
- Performance and security event logging
- Configurable log levels and formats

Logs include: timestamp, level, message, request_id, method, path, status, 
organization_id, api_key_id, duration_ms, and other contextual information.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from flask import Flask, has_request_context
from src.services.request_context import get_request_context, get_request_id


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def __init__(self, json_enabled: bool = True):
        super().__init__()
        self.json_enabled = json_enabled
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON or plain text."""
        if not self.json_enabled:
            # Use standard formatting for plain text logs
            return super().format(record)
        
        # Create structured log entry
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add request context if available
        if has_request_context():
            request_context = get_request_context()
            log_entry.update(request_context)
        
        # Add extra fields from log record
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


class StructuredLogger:
    """Structured logger with request context integration."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.json_enabled = self._get_json_logging_enabled()
    
    def _get_json_logging_enabled(self) -> bool:
        """Check if JSON logging is enabled."""
        return os.environ.get('BRIKK_LOG_JSON', 'true').lower() == 'true'
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with additional context."""
        extra_fields = kwargs.copy()
        
        # Add request_id if not already present
        if 'request_id' not in extra_fields and has_request_context():
            extra_fields['request_id'] = get_request_id()
        
        # Create log record with extra fields
        self.logger.log(level, message, extra={'extra_fields': extra_fields})
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    # Convenience methods for common log types
    def log_request_start(self, method: str, path: str, **kwargs):
        """Log request start."""
        self.info(
            f"Request started: {method} {path}",
            event_type='request_start',
            method=method,
            path=path,
            **kwargs
        )
    
    def log_request_end(self, method: str, path: str, status_code: int, duration_ms: float, **kwargs):
        """Log request completion."""
        self.info(
            f"Request completed: {method} {path} - {status_code} ({duration_ms}ms)",
            event_type='request_end',
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def log_auth_event(self, event: str, success: bool, **kwargs):
        """Log authentication event."""
        level = logging.INFO if success else logging.WARNING
        self._log_with_context(
            level,
            f"Authentication {event}: {'success' if success else 'failure'}",
            event_type='auth_event',
            auth_event=event,
            success=success,
            **kwargs
        )
    
    def log_rate_limit_event(self, scope: str, limit_exceeded: bool, **kwargs):
        """Log rate limiting event."""
        level = logging.WARNING if limit_exceeded else logging.DEBUG
        self._log_with_context(
            level,
            f"Rate limit {'exceeded' if limit_exceeded else 'checked'} for scope: {scope}",
            event_type='rate_limit',
            scope=scope,
            limit_exceeded=limit_exceeded,
            **kwargs
        )
    
    def log_idempotency_event(self, event: str, **kwargs):
        """Log idempotency event."""
        self.info(
            f"Idempotency {event}",
            event_type='idempotency',
            idempotency_event=event,
            **kwargs
        )
    
    def log_security_event(self, event: str, severity: str = 'info', **kwargs):
        """Log security event."""
        level_map = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }
        level = level_map.get(severity.lower(), logging.INFO)
        
        self._log_with_context(
            level,
            f"Security event: {event}",
            event_type='security',
            security_event=event,
            severity=severity,
            **kwargs
        )
    
    def log_performance_event(self, operation: str, duration_ms: float, **kwargs):
        """Log performance event."""
        level = logging.WARNING if duration_ms > 1000 else logging.DEBUG
        self._log_with_context(
            level,
            f"Performance: {operation} took {duration_ms}ms",
            event_type='performance',
            operation=operation,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def log_error_event(self, error: str, error_type: str = 'application', **kwargs):
        """Log error event."""
        self.error(
            f"Error: {error}",
            event_type='error',
            error_type=error_type,
            error_message=error,
            **kwargs
        )


def get_logger(name: str) -> StructuredLogger:
    """Get structured logger instance."""
    return StructuredLogger(name)


def configure_logging(app: Flask):
    """Configure structured logging for Flask application."""
    json_enabled = os.environ.get('BRIKK_LOG_JSON', 'true').lower() == 'true'
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with structured formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredFormatter(json_enabled=json_enabled))
    root_logger.addHandler(console_handler)
    
    # Configure Flask app logger
    app.logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Configure specific loggers
    loggers_to_configure = [
        'brikk.coordination',
        'brikk.auth',
        'brikk.rate_limit',
        'brikk.idempotency',
        'brikk.metrics',
        'brikk.security'
    ]
    
    for logger_name in loggers_to_configure:
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Log configuration
    config_logger = get_logger('brikk.config')
    config_logger.info(
        "Logging configured",
        json_enabled=json_enabled,
        log_level=log_level,
        loggers_configured=loggers_to_configure
    )


class LoggingMiddleware:
    """Middleware for automatic request/response logging."""
    
    def __init__(self, app: Flask):
        self.app = app
        self.logger = get_logger('brikk.requests')
        
        # Register before_request and after_request handlers
        app.before_request(self._before_request)
        app.after_request(self._after_request)
    
    def _before_request(self):
        """Log request start."""
        from flask import request, g
        
        # Skip logging for health checks and metrics to reduce noise
        if request.path in ['/healthz', '/readyz', '/metrics']:
            return
        
        self.logger.log_request_start(
            method=request.method,
            path=request.path,
            remote_addr=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            content_length=request.content_length
        )
    
    def _after_request(self, response):
        """Log request completion."""
        from flask import request, g
        
        # Skip logging for health checks and metrics to reduce noise
        if request.path in ['/healthz', '/readyz', '/metrics']:
            return response
        
        # Calculate duration
        duration_ms = 0
        if hasattr(g, 'request_start_time'):
            duration_ms = round((time.time() - g.request_start_time) * 1000, 2)
        
        # Get auth context if available
        auth_context = {}
        if hasattr(g, 'organization_id') and g.organization_id:
            auth_context['organization_id'] = g.organization_id
        if hasattr(g, 'api_key_id') and g.api_key_id:
            auth_context['api_key_id'] = g.api_key_id
        
        self.logger.log_request_end(
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            content_length=response.content_length,
            **auth_context
        )
        
        return response


def init_logging(app: Flask):
    """Initialize structured logging for Flask application."""
    # Configure logging
    configure_logging(app)
    
    # Initialize logging middleware
    LoggingMiddleware(app)
    
    # Log application startup
    startup_logger = get_logger('brikk.startup')
    startup_logger.info(
        "Application starting",
        flask_env=app.config.get('ENV'),
        debug=app.debug,
        testing=app.testing
    )


# Convenience functions for common logging patterns
def log_auth_success(api_key_id: str, organization_id: str, **kwargs):
    """Log successful authentication."""
    logger = get_logger('brikk.auth')
    logger.log_auth_event(
        'hmac_verification',
        success=True,
        api_key_id=api_key_id,
        organization_id=organization_id,
        **kwargs
    )


def log_auth_failure(reason: str, **kwargs):
    """Log authentication failure."""
    logger = get_logger('brikk.auth')
    logger.log_auth_event(
        'hmac_verification',
        success=False,
        failure_reason=reason,
        **kwargs
    )


def log_rate_limit_hit(scope: str, limit: int, remaining: int, **kwargs):
    """Log rate limit hit."""
    logger = get_logger('brikk.rate_limit')
    logger.log_rate_limit_event(
        scope=scope,
        limit_exceeded=True,
        limit=limit,
        remaining=remaining,
        **kwargs
    )


def log_idempotency_replay(idempotency_key: str, **kwargs):
    """Log idempotency replay."""
    logger = get_logger('brikk.idempotency')
    logger.log_idempotency_event(
        'replay',
        idempotency_key=idempotency_key,
        **kwargs
    )


def log_security_violation(violation_type: str, details: str, **kwargs):
    """Log security violation."""
    logger = get_logger('brikk.security')
    logger.log_security_event(
        f"{violation_type}: {details}",
        severity='warning',
        violation_type=violation_type,
        details=details,
        **kwargs
    )
