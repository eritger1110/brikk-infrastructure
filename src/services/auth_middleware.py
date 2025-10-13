# -*- coding: utf-8 -*-
"""
Authentication middleware for per-org/per-agent API key validation with HMAC v1.
"""
import os
from flask import request, jsonify, g, current_app
from functools import wraps
from typing import Optional, Tuple, Dict, Any

from src.models.api_key import ApiKey
from src.models.org import Organization
from src.models.agent import Agent
from src.services.security_enhanced import HMACSecurityService
from src.services.idempotency import IdempotencyService


class AuthMiddleware:
    """Authentication middleware for HMAC v1 API key validation."""

    def __init__(
            self,
            idempotency_service: Optional[IdempotencyService] = None):
        """Initialize auth middleware with optional idempotency service."""
        self.idempotency_service = idempotency_service or IdempotencyService()
        self.hmac_service = HMACSecurityService()

    def is_feature_enabled(
            self,
            feature_flag: str,
            default: bool = False) -> bool:
        """Check if feature flag is enabled."""
        return os.environ.get(feature_flag,
                              str(default).lower()).lower() == 'true'

    def authenticate_request(
            self) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int]]:
        """
        Authenticate request using HMAC v1 signature validation.

        Returns:
        - (True, None, None): Authentication successful, proceed
        - (False, error_response, status_code): Authentication failed, return error
        """
        try:
            # Check if per-org keys feature is enabled
            if not self.is_feature_enabled(
                    'BRIKK_FEATURE_PER_ORG_KEYS', False):
                # Feature disabled, skip authentication
                return True, None, None

            # Validate required headers
            headers_valid, error_msg, extracted_headers = self.hmac_service.validate_request_headers(
                dict(request.headers))

            if not headers_valid:
                return False, self.hmac_service.create_error_response(
                    'protocol_error', error_msg
                ), 400

            # Extract authentication components
            key_id = extracted_headers['x_brikk_key']
            timestamp = extracted_headers['x_brikk_timestamp']
            signature = extracted_headers['x_brikk_signature']

            # Validate timestamp drift
            timestamp_valid, timestamp_error = self.hmac_service.validate_timestamp_drift(
                timestamp)
            if not timestamp_valid:
                return False, self.hmac_service.create_error_response(
                    'timestamp_error', timestamp_error
                ), 401

            # Get API key from database
            api_key = ApiKey.get_by_key_id(key_id)
            if not api_key or not api_key.is_valid():
                return False, self.hmac_service.create_error_response(
                    'invalid_api_key', 'API key not found or inactive'
                ), 401

            # Get request body and compute hash
            body = request.get_data()
            body_hash = self.hmac_service.compute_body_hash(body)

            # Extract message_id from body for signature verification
            message_id = self.hmac_service.extract_message_id_from_body(body)

            # Verify HMAC signature
            secret = api_key.decrypt_secret()
            signature_valid = self.hmac_service.verify_signature(
                method=request.method,
                path=self.hmac_service.sanitize_path_for_signing(request.path),
                timestamp=timestamp,
                body=body,
                secret=secret,
                provided_signature=signature,
                message_id=message_id
            )

            if not signature_valid:
                # Update failed request count
                api_key.update_usage(success=False)
                return False, self.hmac_service.create_error_response(
                    'invalid_signature', 'HMAC signature verification failed'
                ), 401

            # Check organization limits
            if not api_key.organization.is_within_limits():
                return False, self.hmac_service.create_error_response(
                    'rate_limit_exceeded', 'Organization monthly request limit exceeded'), 429

            # Update successful usage
            api_key.update_usage(success=True)
            api_key.organization.increment_request_count()

            if api_key.agent:
                api_key.agent.update_last_seen()
                api_key.agent.increment_request_count(success=True)

            # Create authentication context
            auth_context = self.hmac_service.create_auth_context(
                organization_id=api_key.organization_id,
                agent_id=api_key.agent_id,
                key_id=key_id,
                scopes=api_key.scopes
            )

            # Store auth context in Flask g for use in route handlers
            g.auth_context = auth_context
            g.api_key = api_key
            g.organization = api_key.organization
            g.agent = api_key.agent

            return True, None, None

        except Exception as e:
            current_app.logger.error(f"Authentication error: {e}")
            return False, self.hmac_service.create_error_response(
                'authentication_error', 'Authentication processing failed'
            ), 500

    def check_idempotency(
            self) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int]]:
        """
        Check request idempotency and return cached response if applicable.

        Returns:
        - (True, None, None): Proceed with request processing
        - (False, response_data, status_code): Return cached/error response immediately
        """
        try:
            # Check if idempotency is enabled
            if not self.is_feature_enabled('BRIKK_IDEM_ENABLED', True):
                return True, None, None

            # Skip idempotency for non-authenticated requests
            if not hasattr(g, 'api_key'):
                return True, None, None

            # Get request body hash
            body = request.get_data()
            body_hash = self.hmac_service.compute_body_hash(body)

            # Check for custom idempotency key
            custom_idempotency_key = request.headers.get('X-Idempotency-Key')

            # Process idempotency check
            should_process, response_data, status_code = self.idempotency_service.process_request_idempotency(
                api_key_id=g.api_key.key_id,
                body_hash=body_hash,
                custom_idempotency_key=custom_idempotency_key
            )

            if not should_process:
                return False, response_data, status_code

            # Store idempotency info for response caching
            g.idempotency_key = self.idempotency_service.generate_idempotency_key(
                g.api_key.key_id, body_hash, custom_idempotency_key)
            g.body_hash = body_hash

            return True, None, None

        except Exception as e:
            current_app.logger.error(f"Idempotency check error: {e}")
            # On error, allow request to proceed (fail open)
            return True, None, None

    def cache_response(
            self, response_data: Dict[str, Any], status_code: int = 200):
        """Cache response for idempotency if enabled and applicable."""
        try:
            if (self.is_feature_enabled('BRIKK_IDEM_ENABLED', True) and
                hasattr(g, 'idempotency_key') and
                    200 <= status_code < 300):

                self.idempotency_service.store_response(
                    idempotency_key=g.idempotency_key,
                    response_data=response_data,
                    status_code=status_code
                )
        except Exception as e:
            current_app.logger.error(f"Response caching error: {e}")
            # Don't fail the request if caching fails


def require_hmac_auth(f):
    """
    Decorator to require HMAC v1 authentication for route handlers.

    Only applies when BRIKK_FEATURE_PER_ORG_KEYS=true.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_middleware = AuthMiddleware()

        # Authenticate request
        auth_success, auth_error, auth_status = auth_middleware.authenticate_request()
        if not auth_success:
            return jsonify(auth_error), auth_status

        # Check idempotency
        idem_success, idem_response, idem_status = auth_middleware.check_idempotency()
        if not idem_success:
            return jsonify(idem_response), idem_status

        # Execute route handler
        result = f(*args, **kwargs)

        # Cache response for idempotency if applicable
        if isinstance(result, tuple) and len(result) == 2:
            response_data, status_code = result
            if isinstance(response_data, dict):
                auth_middleware.cache_response(response_data, status_code)
        elif hasattr(result, 'get_json') and hasattr(result, 'status_code'):
            # Flask Response object
            try:
                response_data = result.get_json()
                if response_data:
                    auth_middleware.cache_response(
                        response_data, result.status_code)
            except BaseException:
                pass  # Skip caching if response is not JSON

        return result

    return decorated_function


def get_auth_context() -> Optional[Dict[str, Any]]:
    """Get authentication context from Flask g."""
    return getattr(g, 'auth_context', None)


def get_authenticated_organization() -> Optional[Organization]:
    """Get authenticated organization from Flask g."""
    return getattr(g, 'organization', None)


def get_authenticated_agent() -> Optional[Agent]:
    """Get authenticated agent from Flask g."""
    return getattr(g, 'agent', None)


def get_api_key() -> Optional[ApiKey]:
    """Get API key from Flask g."""
    return getattr(g, 'api_key', None)


def is_scope_allowed(required_scope: str) -> bool:
    """Check if current authentication context has required scope."""
    auth_context = get_auth_context()
    if not auth_context:
        return False

    scopes = auth_context.get('scopes', [])
    return required_scope in scopes or 'admin' in scopes


def require_scope(scope: str):
    """Decorator to require specific scope for route access."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_scope_allowed(scope):
                return jsonify({
                    'code': 'insufficient_scope',
                    'message': f'Required scope: {scope}',
                    'request_id': HMACSecurityService.generate_request_id()
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
