'''
Coordination routes for Brikk API.

Contains both existing coordination endpoints and new v1 API with envelope validation,
HMAC v1 authentication, and Redis idempotency.
'''

import os
import hashlib
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt
from pydantic import ValidationError
from src.models import Agent, Coordination
from src.database import db
from datetime import datetime, timezone
import time
import random

from src.services.request_guards import apply_request_guards_to_blueprint
from src.services.security_headers import apply_security_headers_to_blueprint
from src.schemas.envelope import Envelope
from src.services.structured_logging import get_logger, log_auth_success, log_auth_failure, log_rate_limit_hit, log_idempotency_replay
from src.services.metrics import record_rate_limit_hit, record_idempotency_replay
from src.services.request_context import set_auth_context


# Single coordination blueprint for all coordination endpoints
bp = Blueprint("coordination", __name__)

# Initialize logger for coordination module
logger = get_logger('brikk.coordination')

# Apply security headers to all coordination routes
apply_security_headers_to_blueprint(bp)


# ===== EXISTING COORDINATION ENDPOINTS =====

@bp.post("/api/coordination/run")
@jwt_required()
def run():
    '''
    Simple user-facing orchestration endpoint.
    Replace the body of this function with your real pipeline/orchestrator call.
    '''
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


@bp.get("/api/metrics")
@jwt_required()
def metrics():
    '''
    Minimal metrics for the dashboard graphs.
    Replace with your real metrics collection if available.
    '''
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
# apply_request_guards_to_blueprint(coordination_v1_bp)
apply_security_headers_to_blueprint(coordination_v1_bp)

def generate_request_id() -> str:
    '''Generate a unique request ID for error tracking.'''
    import uuid
    return str(uuid.uuid4())

def get_feature_flag(flag_name: str, default: str = "false") -> bool:
    '''Get feature flag value from environment.'''
    return os.environ.get(flag_name, default).lower() == "true"

def create_error_response(code: str, message: str, status_code: int = 400, details: list = None) -> tuple:
    '''Create standardized error response.'''
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
    '''
    Coordination API endpoint v1 with layered security.
    
    Security layers (in order):
    1. Request guards: Content-Type, body size, required headers (via middleware)
    2. HMAC v1 authentication: X-Brikk-Key, X-Brikk-Timestamp, X-Brikk-Signature
    3. Timestamp drift check: +/-300 seconds
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
    '''
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
                # Log authentication failure
                log_auth_failure(
                    reason=auth_error.get('code', 'unknown'),
                    request_id=request_id,
                    status_code=auth_status
                )
                logger.log_auth_event('hmac_verification', success=False, 
                                    failure_reason=auth_error.get('code', 'unknown'),
                                    request_id=request_id)
                return jsonify(auth_error), auth_status
            else:
                # Log successful authentication and set auth context
                if hasattr(g, 'auth_context') and g.auth_context:
                    log_auth_success(
                        api_key_id=g.auth_context.get('key_id'),
                        organization_id=g.auth_context.get('org_id'),
                        request_id=request_id
                    )
                    logger.log_auth_event('hmac_verification', success=True,
                                        api_key_id=g.auth_context.get('key_id'),
                                        organization_id=g.auth_context.get('org_id'),
                                        request_id=request_id)
        
        # Step 2: Rate Limiting (if enabled)
        rate_limit_result = auth_service.check_rate_limit(request_id)
        if rate_limit_result and not rate_limit_result.allowed:
            # Log rate limit hit
            scope = getattr(g, 'organization_id', 'anonymous') if hasattr(g, 'organization_id') else 'anonymous'
            log_rate_limit_hit(
                scope=scope,
                limit=rate_limit_result.limit,
                remaining=rate_limit_result.remaining,
                request_id=request_id
            )
            record_rate_limit_hit(scope)
            logger.log_rate_limit_event(scope=scope, limit_exceeded=True,
                                      limit=rate_limit_result.limit,
                                      remaining=rate_limit_result.remaining,
                                      request_id=request_id)
            
            error_response = auth_service.create_error_response(
                "rate_limited",
                "Rate limit exceeded",
                429,
                request_id=request_id
            )
            response = jsonify(error_response)
            # Add rate limit headers to 429 response
            if rate_limit_result:
                for header, value in rate_limit_result.to_headers().items():
                    response.headers[header] = value
            return response, 429
        
        # Step 3: Idempotency Check (if enabled)
        if auth_service.get_feature_flag("BRIKK_IDEM_ENABLED"):
            should_process, idem_response, idem_status = auth_service.check_idempotency(body_hash, request_id)
            if not should_process:
                # Log idempotency replay
                idempotency_key = request.headers.get('Idempotency-Key', body_hash[:16])
                log_idempotency_replay(idempotency_key=idempotency_key, request_id=request_id)
                record_idempotency_replay()
                logger.log_idempotency_event('replay', idempotency_key=idempotency_key,
                                           request_id=request_id, status_code=idem_status)
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
            import traceback
            traceback.print_exc()
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
        
        # Log successful request processing
        logger.info(
            f"Coordination request processed successfully",
            event_type='coordination_success',
            message_id=envelope.message_id,
            message_type=envelope.type,
            sender_agent_id=envelope.sender.agent_id,
            recipient_agent_id=envelope.recipient.agent_id,
            ttl_ms=envelope.ttl_ms,
            request_id=request_id
        )
        
        # Step 6: Cache response for idempotency (if enabled)
        if auth_service.get_feature_flag("BRIKK_IDEM_ENABLED"):
            auth_service.cache_response(body_hash, response_data, 202)
            logger.log_idempotency_event('cache_stored', 
                                       idempotency_key=request.headers.get('Idempotency-Key', body_hash[:16]),
                                       request_id=request_id)
        
        # Create response with rate limit headers
        response = jsonify(response_data)
        
        # Add rate limit headers to success response
        if rate_limit_result:
            for header, value in rate_limit_result.to_headers().items():
                response.headers[header] = value
        
        return response, 202
        
    except Exception as e:
        import traceback
        traceback.print_exc()
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
    '''
    Health check endpoint for the coordination API.
    
    Returns basic status information without requiring authentication
    or request validation.
    '''
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
bp.register_blueprint(coordination_v1_bp)

