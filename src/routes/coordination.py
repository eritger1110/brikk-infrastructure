# src/routes/coordination.py
"""
Coordination routes for Brikk API.

Contains both existing coordination endpoints and new v1 API with envelope validation,
HMAC v1 authentication, and Redis idempotency.
"""

import os
import hashlib
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt
from pydantic import ValidationError
from src.models.agent import Agent, Coordination, db
from datetime import datetime, timezone
import time
import random

from src.services.request_guards import apply_request_guards_to_blueprint
from src.services.security_headers import apply_security_headers_to_blueprint
from src.schemas.envelope import Envelope


# Single coordination blueprint for all coordination endpoints
coordination_bp = Blueprint("coordination_bp", __name__)

# Apply security headers to all coordination routes
apply_security_headers_to_blueprint(coordination_bp)


# ===== EXISTING COORDINATION ENDPOINTS =====

@coordination_bp.post("/api/coordination/run")
@jwt_required()
def run():
    """
    Simple user-facing orchestration endpoint.
    Replace the body of this function with your real pipeline/orchestrator call.
    """
    claims = get_jwt()
    email = claims.get("email")

    data = request.get_json() or {}
    prompt = data.get("prompt", "")

    # --- DEMO implementation (replace with real logic) ---
    start = time.time()
    time.sleep(0.15)  # pretend work
    output = f"[Brikk demo] User={email} Prompt={prompt!r} -> processed"
    duration_ms = round((time.time() - start) * 1000, 2)

    return jsonify({
        "ok": True,
        "output": output,
        "latency_ms": duration_ms
    })


@coordination_bp.get("/api/metrics")
@jwt_required()
def metrics():
    """
    Minimal metrics for the dashboard graphs.
    Replace with your real metrics collection if available.
    """
    total_agents   = Agent.query.count()
    active_agents  = Agent.query.filter_by(status='active').count()

    # Fake "today" numbers if you haven't populated Coordination yet
    total_coord = Coordination.query.count()
    completed   = Coordination.query.filter_by(status="completed").count()
    success_rate = round((completed / max(total_coord, 1)) * 100, 2)

    # Some sample series (client will chart these)
    series = {
        "last10m": [random.randint(1, 8) for _ in range(10)],
        "latency": [random.randint(80, 220) for _ in range(10)],
    }

    return jsonify({
        "active_agents": active_agents,
        "total_agents": total_agents,
        "total_coordinations": total_coord,
        "success_rate": success_rate,
        "series": series,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


# ===== NEW V1 API WITH ENVELOPE VALIDATION =====

# Create a sub-blueprint for v1 API with request guards
coordination_v1_bp = Blueprint("coordination_v1", __name__)
apply_request_guards_to_blueprint(coordination_v1_bp)
apply_security_headers_to_blueprint(coordination_v1_bp)


def generate_request_id() -> str:
    """Generate a unique request ID for error tracking."""
    import uuid
    return str(uuid.uuid4())


def get_feature_flag(flag_name: str, default: str = "false") -> bool:
    """Get feature flag value from environment."""
    return os.environ.get(flag_name, default).lower() == "true"


def create_error_response(code: str, message: str, status_code: int = 400, details: list = None) -> tuple:
    """Create standardized error response."""
    error_data = {
        "code": code,
        "message": message,
        "request_id": generate_request_id()
    }
    if details:
        error_data["details"] = details
    
    return jsonify(error_data), status_code


@coordination_v1_bp.route("/api/v1/coordination", methods=["POST"])
def coordination_endpoint():
    """
    Coordination API endpoint v1 with layered security.
    
    Security layers (in order):
    1. Request guards: Content-Type, body size, required headers (via middleware)
    2. HMAC v1 authentication: X-Brikk-Key, X-Brikk-Timestamp, X-Brikk-Signature
    3. Timestamp drift check: ±300 seconds
    4. Redis idempotency: Duplicate request detection
    5. Envelope validation: Pydantic schema validation
    
    Feature flags:
    - BRIKK_FEATURE_PER_ORG_KEYS=true: Enable HMAC v1 authentication
    - BRIKK_IDEM_ENABLED=true: Enable Redis idempotency checking
    - BRIKK_ALLOW_UUID4=false: Enforce UUIDv7 in envelope validation
    
    Returns:
    - 202: Accepted with echo of message_id
    - 400: Protocol error (missing headers, wrong content-type, etc.)
    - 401: Authentication failed (invalid key, signature, timestamp drift)
    - 409: Idempotency conflict (same key, different body)
    - 413: Request body too large
    - 415: Wrong content-type
    - 422: Envelope validation error
    - 429: Rate limit exceeded
    """
    from src.services.coordination_auth import CoordinationAuthService
    
    auth_service = CoordinationAuthService()
    request_id = auth_service.generate_request_id()
    
    try:
        # Get raw request body for HMAC verification and idempotency
        raw_body = request.get_data()
        body_hash = hashlib.sha256(raw_body).hexdigest()
        
        # Step 1: HMAC Authentication (if enabled)
        if auth_service.get_feature_flag("BRIKK_FEATURE_PER_ORG_KEYS"):
            auth_success, auth_error, auth_status = auth_service.authenticate_request(raw_body, request_id)
            if not auth_success:
                return jsonify(auth_error), auth_status
        
        # Step 2: Idempotency Check (if enabled)
        if auth_service.get_feature_flag("BRIKK_IDEM_ENABLED"):
            should_process, idem_response, idem_status = auth_service.check_idempotency(body_hash, request_id)
            if not should_process:
                return jsonify(idem_response), idem_status
        
        # Step 3: Parse and validate JSON
        try:
            json_data = request.get_json()
            if json_data is None:
                error_response = auth_service.create_error_response(
                    "protocol_error",
                    "Request body must contain valid JSON",
                    400,
                    request_id=request_id
                )
                return jsonify(error_response), 400
        except Exception as e:
            error_response = auth_service.create_error_response(
                "protocol_error",
                f"Invalid JSON in request body: {str(e)}",
                400,
                request_id=request_id
            )
            return jsonify(error_response), 400
        
        # Step 4: Validate envelope schema
        try:
            envelope = Envelope(**json_data)
        except ValidationError as e:
            # Format Pydantic validation errors
            error_details = []
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                error_details.append(f"{field_path}: {error['msg']}")
            
            error_response = auth_service.create_error_response(
                "validation_error",
                "Envelope validation failed",
                422,
                error_details,
                request_id
            )
            return jsonify(error_response), 422
        
        # Step 5: Process the validated request
        response_data = {
            "status": "accepted",
            "echo": {
                "message_id": envelope.message_id
            }
        }
        
        # Add authentication context if available
        auth_context = auth_service.get_auth_context_for_response()
        if auth_context:
            response_data["auth"] = auth_context
        
        # Step 6: Cache response for idempotency (if enabled)
        if auth_service.get_feature_flag("BRIKK_IDEM_ENABLED"):
            auth_service.cache_response(body_hash, response_data, 202)
        
        return jsonify(response_data), 202
        
    except Exception as e:
        # Log the error for debugging (in production, use proper logging)
        print(f"Coordination endpoint error: {str(e)}")
        
        error_response = auth_service.create_error_response(
            "internal_error",
            "An unexpected error occurred",
            500,
            request_id=request_id
        )
        return jsonify(error_response), 500





@coordination_v1_bp.route("/api/v1/coordination/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for the coordination API.
    
    Returns basic status information without requiring authentication
    or request validation.
    """
    from src.services.coordination_auth import CoordinationAuthService
    
    auth_service = CoordinationAuthService()
    feature_flags = auth_service.validate_feature_flags()
    
    return jsonify({
        "status": "healthy",
        "service": "coordination-api",
        "version": "1.0",
        "features": feature_flags
    }), 200


# Register the v1 sub-blueprint with the main coordination blueprint
coordination_bp.register_blueprint(coordination_v1_bp)
