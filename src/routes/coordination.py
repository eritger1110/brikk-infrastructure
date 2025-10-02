# src/routes/coordination.py
"""
Coordination routes for Brikk API.

Contains both existing coordination endpoints and new v1 API with envelope validation.
"""

import os
from flask import Blueprint, request, jsonify
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


@coordination_v1_bp.route("/api/v1/coordination", methods=["POST"])
def coordination_endpoint():
    """
    Coordination API endpoint v1 (stub implementation).
    
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
                "request_id": generate_request_id()
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
                "request_id": generate_request_id()
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
            "request_id": generate_request_id()
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


# Register the v1 sub-blueprint with the main coordination blueprint
coordination_bp.register_blueprint(coordination_v1_bp)
