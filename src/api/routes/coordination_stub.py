"""
Stub coordination route for Brikk API v1.

This is a minimal implementation that validates the envelope schema
and returns an acceptance response. No queue/DB/signing logic yet.

POST /api/v1/coordination
- Validates request guards (headers, content-type, body size)
- Validates envelope schema with Pydantic
- Returns 202 with echo of message_id
"""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from src.api.middleware.request_guards import apply_request_guards_to_blueprint
from src.api.middleware.security_headers import apply_security_headers_to_blueprint
from src.api.models.envelope import Envelope


# Create blueprint for coordination API v1
coordination_v1_bp = Blueprint("coordination_v1", __name__)

# Apply middleware to all routes in this blueprint
apply_request_guards_to_blueprint(coordination_v1_bp)
apply_security_headers_to_blueprint(coordination_v1_bp)


@coordination_v1_bp.route("/api/v1/coordination", methods=["POST"])
def coordination_endpoint():
    """
    Coordination API endpoint (stub implementation).
    
    Validates:
    - Request guards (via middleware): Content-Type, body size, required headers
    - Envelope schema: Pydantic validation of message structure
    
    Returns:
    - 202: Accepted with echo of message_id
    - 400: Protocol error (missing headers, wrong content-type, etc.)
    - 413: Request body too large
    - 415: Wrong content-type
    - 422: Envelope validation error
    """
    try:
        # Get JSON data from request
        json_data = request.get_json()
        
        if json_data is None:
            return jsonify({
                "code": "protocol_error",
                "message": "Request body must contain valid JSON",
                "request_id": "stub-" + str(hash(request.url))[:8]
            }), 400
        
        # Validate envelope schema with Pydantic
        try:
            envelope = Envelope(**json_data)
        except ValidationError as e:
            # Format Pydantic validation errors for API response
            error_details = []
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                error_details.append(f"{field_path}: {error['msg']}")
            
            return jsonify({
                "code": "validation_error",
                "message": "Envelope validation failed",
                "details": error_details,
                "request_id": "stub-" + str(hash(request.url))[:8]
            }), 422
        
        # Envelope validation successful
        # In a real implementation, this would:
        # 1. Verify HMAC signature
        # 2. Check timestamp drift
        # 3. Queue the message for processing
        # 4. Store in database
        # 5. Return job/tracking ID
        
        # For now, just return acceptance with echo
        return jsonify({
            "status": "accepted",
            "echo": {
                "message_id": envelope.message_id
            }
        }), 202
        
    except Exception as e:
        # Catch any unexpected errors
        return jsonify({
            "code": "internal_error",
            "message": "An unexpected error occurred",
            "request_id": "stub-" + str(hash(request.url))[:8]
        }), 500


@coordination_v1_bp.route("/api/v1/coordination/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for the coordination API.
    
    Returns basic status information without requiring authentication
    or request validation.
    """
    return jsonify({
        "status": "healthy",
        "service": "coordination-api",
        "version": "1.0-stub"
    }), 200
