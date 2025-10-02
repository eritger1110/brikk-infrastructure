"""
Request guards middleware for Brikk API coordination endpoints.

Enforces:
- Content-Type: application/json
- Max body size: 256 KB
- Required headers: X-Brikk-Key, X-Brikk-Timestamp, X-Brikk-Signature
"""

import uuid
from functools import wraps
from typing import Callable, Any

from flask import request, jsonify, current_app


# Maximum request body size in bytes (256 KB)
MAX_BODY_SIZE = 256 * 1024


def generate_request_id() -> str:
    """Generate a unique request ID for error tracking."""
    return str(uuid.uuid4())


def create_error_response(code: str, message: str, status_code: int = 400) -> tuple:
    """Create standardized error response with request ID."""
    request_id = generate_request_id()
    return jsonify({
        "code": code,
        "message": message,
        "request_id": request_id
    }), status_code


def validate_content_type() -> tuple | None:
    """Validate that Content-Type is application/json."""
    content_type = request.headers.get('Content-Type', '')
    
    # Handle charset parameter in content type
    if not content_type.startswith('application/json'):
        return create_error_response(
            "protocol_error",
            "Content-Type must be application/json",
            415
        )
    return None


def validate_body_size() -> tuple | None:
    """Validate that request body doesn't exceed maximum size."""
    content_length = request.headers.get('Content-Length')
    
    if content_length:
        try:
            size = int(content_length)
            if size > MAX_BODY_SIZE:
                return create_error_response(
                    "protocol_error",
                    f"Request body too large. Maximum size: {MAX_BODY_SIZE} bytes",
                    413
                )
        except ValueError:
            return create_error_response(
                "protocol_error",
                "Invalid Content-Length header",
                400
            )
    
    # Also check actual data size if available
    if hasattr(request, 'data') and len(request.data) > MAX_BODY_SIZE:
        return create_error_response(
            "protocol_error",
            f"Request body too large. Maximum size: {MAX_BODY_SIZE} bytes",
            413
        )
    
    return None


def validate_required_headers() -> tuple | None:
    """Validate that all required Brikk headers are present."""
    required_headers = [
        'X-Brikk-Key',
        'X-Brikk-Timestamp', 
        'X-Brikk-Signature'
    ]
    
    missing_headers = []
    for header in required_headers:
        if not request.headers.get(header):
            missing_headers.append(header)
    
    if missing_headers:
        return create_error_response(
            "protocol_error",
            f"Missing required headers: {', '.join(missing_headers)}",
            400
        )
    
    return None


def request_guards(f: Callable) -> Callable:
    """
    Decorator that applies all request validation guards.
    
    Validates:
    - Content-Type: application/json
    - Body size <= 256 KB
    - Required headers: X-Brikk-Key, X-Brikk-Timestamp, X-Brikk-Signature
    
    Returns 400/413/415 with standardized error format on validation failure.
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # Skip validation for non-POST requests
        if request.method != 'POST':
            return f(*args, **kwargs)
        
        # Validate Content-Type
        error_response = validate_content_type()
        if error_response:
            return error_response
        
        # Validate body size
        error_response = validate_body_size()
        if error_response:
            return error_response
        
        # Validate required headers
        error_response = validate_required_headers()
        if error_response:
            return error_response
        
        # All validations passed, proceed with the request
        return f(*args, **kwargs)
    
    return decorated_function


def apply_request_guards_to_blueprint(blueprint) -> None:
    """
    Apply request guards to all routes in a blueprint.
    
    This is an alternative to decorating individual routes.
    """
    @blueprint.before_request
    def before_request():
        # Skip validation for non-POST requests
        if request.method != 'POST':
            return None
        
        # Validate Content-Type
        error_response = validate_content_type()
        if error_response:
            return error_response
        
        # Validate body size
        error_response = validate_body_size()
        if error_response:
            return error_response
        
        # Validate required headers
        error_response = validate_required_headers()
        if error_response:
            return error_response
        
        # All validations passed
        return None
