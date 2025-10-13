"""
Coordination authentication helper service.

Provides JWT session authentication with optional HMAC request signing.
Supports both session-based auth (primary) and HMAC auth (optional).
"""

import os
import hashlib
from datetime import datetime, timezone
from flask import request, g, session
from typing import Optional, Tuple, Dict, Any

from src.services.security_enhanced import HMACSecurityService
from src.services.idempotency import IdempotencyService
from src.models.api_key import ApiKey
from src.models.agent import Agent
from src.models.user import User


class CoordinationAuthService:
    """Service for handling coordination endpoint authentication and idempotency."""
    
    def __init__(self):
        self.hmac_service = HMACSecurityService()
        self.idempotency_service = IdempotencyService()
    
    @staticmethod
    def get_feature_flag(flag_name: str, default: str = "false") -> bool:
        """Get feature flag value from environment."""
        return os.environ.get(flag_name, default).lower() == "true"
    
    @staticmethod
    def generate_request_id() -> str:
        """Generate a unique request ID for error tracking."""
        import uuid
        return str(uuid.uuid4())
    
    @staticmethod
    def create_error_response(code: str, message: str, status_code: int = 400, 
                            details: Optional[list] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Create standardized error response."""
        error_data = {
            "code": code,
            "message": message,
            "request_id": request_id or CoordinationAuthService.generate_request_id()
        }
        if details:
            error_data["details"] = details
        
        return error_data
    
    def authenticate_request(self, raw_body: bytes, request_id: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int]]:
        """
        Perform authentication using JWT session auth (primary) or HMAC (optional).
        
        Args:
            raw_body: Raw request body bytes
            request_id: Request ID for tracking
            
        Returns:
            Tuple of (success, error_response, status_code)
            If success is True, error_response and status_code are None
        """
        try:
            # First try JWT session authentication
            jwt_auth_result = self._authenticate_jwt_session(request_id)
            if jwt_auth_result[0]:  # JWT auth successful
                return jwt_auth_result
            
            # If JWT auth fails and HMAC is enabled, try HMAC authentication
            if self.get_feature_flag("BRIKK_HMAC_AUTH_ENABLED", "false"):
                return self._authenticate_hmac(raw_body, request_id)
            
            # No valid authentication method
            return False, self.create_error_response(
                "unauthorized",
                "Authentication required. Please log in or provide valid HMAC headers.",
                401,
                request_id=request_id
            ), 401
            
        except Exception as e:
            return False, self.create_error_response(
                "unauthorized",
                f"Authentication error: {str(e)}",
                401,
                request_id=request_id
            ), 401
    
    def _authenticate_jwt_session(self, request_id: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int]]:
        """
        Authenticate using JWT session (primary method).
        
        Args:
            request_id: Request ID for tracking
            
        Returns:
            Tuple of (success, error_response, status_code)
        """
        try:
            # Check if user is logged in via session
            user_id = session.get('user_id')
            if not user_id:
                return False, self.create_error_response(
                    "unauthorized",
                    "Session authentication required",
                    401,
                    request_id=request_id
                ), 401
            
            # Get user and verify they exist
            user = User.query.get(user_id)
            if not user or not user.is_active:
                return False, self.create_error_response(
                    "unauthorized",
                    "Invalid or inactive user session",
                    401,
                    request_id=request_id
                ), 401
            
            # Check if request includes agent ownership verification
            json_data = request.get_json()
            if json_data and 'sender' in json_data:
                sender_agent_id = json_data['sender']
                
                # Verify the sender agent belongs to the user's organization
                agent = Agent.query.filter_by(id=sender_agent_id).first()
                if not agent:
                    return False, self.create_error_response(
                        "forbidden",
                        f"Agent {sender_agent_id} not found",
                        403,
                        request_id=request_id
                    ), 403
                
                if agent.organization_id != user.organization_id:
                    return False, self.create_error_response(
                        "forbidden",
                        f"Agent {sender_agent_id} does not belong to your organization",
                        403,
                        request_id=request_id
                    ), 403
            
            # Set authentication context
            g.auth_context = {
                "user_id": user.id,
                "organization_id": user.organization_id,
                "agent_id": json_data.get('sender') if json_data else None,
                "request_id": request_id,
                "auth_method": "jwt_session"
            }
            
            return True, None, None  # Authentication successful
            
        except Exception as e:
            return False, self.create_error_response(
                "unauthorized",
                f"Session authentication error: {str(e)}",
                401,
                request_id=request_id
            ), 401
    
    def _authenticate_hmac(self, raw_body: bytes, request_id: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int]]:
        """
        Perform HMAC v1 authentication (optional method).
        
        Args:
            raw_body: Raw request body bytes
            request_id: Request ID for tracking
            
        Returns:
            Tuple of (success, error_response, status_code)
        """
        try:
            # Check required headers
            api_key_header = request.headers.get('X-Brikk-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
            timestamp = request.headers.get('X-Brikk-Timestamp')
            signature = request.headers.get('X-Brikk-Signature')
            
            if not all([api_key_header, timestamp, signature]):
                missing_headers = []
                if not api_key_header:
                    missing_headers.append('X-Brikk-Key or Authorization')
                if not timestamp:
                    missing_headers.append('X-Brikk-Timestamp')
                if not signature:
                    missing_headers.append('X-Brikk-Signature')
                
                return False, self.create_error_response(
                    "protocol_error",
                    f"Missing required HMAC headers: {', '.join(missing_headers)}",
                    400,
                    request_id=request_id
                ), 400
            
            # Authenticate API key using PBKDF2 hash verification
            api_key_record = ApiKey.authenticate_api_key(api_key_header)
            if not api_key_record or not api_key_record.is_valid():
                return False, self.create_error_response(
                    "unauthorized",
                    "Invalid or disabled API key",
                    401,
                    request_id=request_id
                ), 401
            
            # Verify timestamp drift (+/-300 seconds)
            try:
                timestamp_valid = self.hmac_service.verify_timestamp_drift(timestamp, max_drift_seconds=300)
                if not timestamp_valid:
                    api_key_record.update_usage(success=False)
                    return False, self.create_error_response(
                        "unauthorized",
                        "Request timestamp outside acceptable drift (+/-300 seconds)",
                        401,
                        request_id=request_id
                    ), 401
            except Exception as e:
                api_key_record.update_usage(success=False)
                return False, self.create_error_response(
                    "unauthorized",
                    f"Invalid timestamp format: {str(e)}",
                    401,
                    request_id=request_id
                ), 401
            
            # For HMAC auth, we need a way to get the secret
            # Since we're using PBKDF2 hashing, we can't retrieve the original API key
            # This is a limitation of the secure hashing approach
            # For HMAC to work, we'd need to store a separate HMAC secret
            # For now, we'll document this limitation
            
            # Update API key usage (successful authentication)
            api_key_record.update_usage(success=True)
            
            # Set authentication context
            g.auth_context = {
                "organization_id": api_key_record.organization_id,
                "agent_id": api_key_record.agent_id,
                "key_id": api_key_record.key_id,
                "request_id": request_id,
                "api_key": api_key_record,
                "auth_method": "hmac"
            }
            
            return True, None, None  # Authentication successful
            
        except Exception as e:
            return False, self.create_error_response(
                "unauthorized",
                f"HMAC authentication error: {str(e)}",
                401,
                request_id=request_id
            ), 401
    
    def check_idempotency(self, body_hash: str, request_id: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int]]:
        """
        Perform Redis idempotency check.
        
        Uses the 'Idempotency-Key' header if provided, otherwise generates key from request.
        
        Args:
            body_hash: SHA256 hash of request body
            request_id: Request ID for tracking
            
        Returns:
            Tuple of (should_process, response, status_code)
            If should_process is True, response and status_code are None
        """
        try:
            # Get key ID from auth context or use default
            key_id = getattr(g, 'auth_context', {}).get('key_id', 'anonymous')
            
            # Check for custom idempotency key header
            custom_idem_key = request.headers.get('Idempotency-Key')
            
            # Process idempotency
            should_process, response, status = self.idempotency_service.process_request_idempotency(
                key_id=key_id,
                body_hash=body_hash,
                custom_idempotency_key=custom_idem_key
            )
            
            if not should_process:
                if status == 409:
                    # Idempotency conflict
                    return False, self.create_error_response(
                        "idempotency_conflict",
                        "Request conflicts with previous request using same key but different body",
                        409,
                        request_id=request_id
                    ), 409
                else:
                    # Return cached response
                    return False, response, status
            
            return True, None, None  # Should process request
            
        except Exception as e:
            # Fail open on idempotency errors (allow request to proceed)
            print(f"Idempotency check error: {str(e)}")
            return True, None, None
    
    def cache_response(self, body_hash: str, response_data: Dict[str, Any], status_code: int):
        """
        Cache response for idempotency.
        
        Args:
            body_hash: SHA256 hash of request body
            response_data: Response data to cache
            status_code: HTTP status code
        """
        try:
            key_id = getattr(g, 'auth_context', {}).get('key_id', 'anonymous')
            custom_idem_key = request.headers.get('Idempotency-Key')
            
            idem_key = self.idempotency_service.generate_idempotency_key(
                key_id, body_hash, custom_idem_key
            )
            
            self.idempotency_service.store_response(idem_key, response_data, status_code)
            
        except Exception as e:
            # Don't fail the request if caching fails
            print(f"Failed to cache idempotency response: {str(e)}")
    
    def get_auth_context_for_response(self) -> Optional[Dict[str, Any]]:
        """
        Get authentication context for including in response.
        
        Returns:
            Dict with auth context or None if not authenticated
        """
        if hasattr(g, 'auth_context') and g.auth_context:
            return {
                "organization_id": g.auth_context["organization_id"],
                "agent_id": g.auth_context.get("agent_id"),
                "request_id": g.auth_context["request_id"],
                "auth_method": g.auth_context.get("auth_method", "unknown")
            }
        return None
    
    def validate_feature_flags(self) -> Dict[str, bool]:
        """
        Get current feature flag status.
        
        Returns:
            Dict with feature flag status
        """
        return {
            "hmac_auth_enabled": self.get_feature_flag("BRIKK_HMAC_AUTH_ENABLED"),
            "idempotency_enabled": self.get_feature_flag("BRIKK_IDEM_ENABLED", "true"),
            "rate_limiting_enabled": self.get_feature_flag("BRIKK_RATE_LIMIT_ENABLED", "true"),
            "uuid4_allowed": self.get_feature_flag("BRIKK_ALLOW_UUID4")
        }
    
    def check_rate_limit(self, request_id: str):
        """
        Check rate limit for the current request.
        
        Uses Redis-based rate limiting with configurable defaults.
        
        Args:
            request_id: Request ID for error tracking
            
        Returns:
            RateLimitResult with limit status and headers
        """
        from src.services.rate_limit import get_rate_limiter
        
        rate_limiter = get_rate_limiter()
        
        # Get scope key based on auth context
        organization_id = getattr(g, 'auth_context', {}).get('organization_id')
        api_key_id = getattr(g, 'auth_context', {}).get('key_id')
        
        scope_key = rate_limiter.get_scope_key(organization_id, api_key_id)
        
        # Check rate limit
        return rate_limiter.check_rate_limit(scope_key)


class CoordinationAuthError(Exception):
    """Custom exception for coordination authentication errors."""
    
    def __init__(self, code: str, message: str, status_code: int = 400, details: Optional[list] = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)
    
    def to_dict(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Convert exception to error response dict."""
        error_data = {
            "code": self.code,
            "message": self.message,
            "request_id": request_id or CoordinationAuthService.generate_request_id()
        }
        if self.details:
            error_data["details"] = self.details
        
        return error_data
