"""
Coordination authentication helper service.

Provides centralized authentication and idempotency logic for the coordination endpoint.
"""

import os
import hashlib
from datetime import datetime, timezone
from flask import request, g
from typing import Optional, Tuple, Dict, Any

from src.services.security_enhanced import HMACSecurityService
from src.services.idempotency import IdempotencyService
from src.models.api_key import ApiKey


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
        Perform HMAC v1 authentication.
        
        Args:
            raw_body: Raw request body bytes
            request_id: Request ID for tracking
            
        Returns:
            Tuple of (success, error_response, status_code)
            If success is True, error_response and status_code are None
        """
        try:
            # Check required headers
            api_key_id = request.headers.get('X-Brikk-Key')
            timestamp = request.headers.get('X-Brikk-Timestamp')
            signature = request.headers.get('X-Brikk-Signature')
            
            if not all([api_key_id, timestamp, signature]):
                missing_headers = []
                if not api_key_id:
                    missing_headers.append('X-Brikk-Key')
                if not timestamp:
                    missing_headers.append('X-Brikk-Timestamp')
                if not signature:
                    missing_headers.append('X-Brikk-Signature')
                
                return False, self.create_error_response(
                    "protocol_error",
                    f"Missing required headers: {', '.join(missing_headers)}",
                    400,
                    request_id=request_id
                ), 400
            
            # Look up API key
            api_key = ApiKey.query.filter_by(key_id=api_key_id).first()
            if not api_key or not api_key.is_valid():
                # Update failed usage if key exists
                if api_key:
                    api_key.update_usage(success=False)
                
                return False, self.create_error_response(
                    "unauthorized",
                    "Invalid or disabled API key",
                    401,
                    request_id=request_id
                ), 401
            
            # Decrypt secret
            try:
                secret = api_key.decrypt_secret()
            except Exception as e:
                api_key.update_usage(success=False)
                return False, self.create_error_response(
                    "unauthorized",
                    "Failed to decrypt API key secret",
                    401,
                    request_id=request_id
                ), 401
            
            # Verify timestamp drift (±300 seconds)
            try:
                timestamp_valid = self.hmac_service.verify_timestamp_drift(timestamp, max_drift_seconds=300)
                if not timestamp_valid:
                    api_key.update_usage(success=False)
                    return False, self.create_error_response(
                        "unauthorized",
                        "Request timestamp outside acceptable drift (±300 seconds)",
                        401,
                        request_id=request_id
                    ), 401
            except Exception as e:
                api_key.update_usage(success=False)
                return False, self.create_error_response(
                    "unauthorized",
                    f"Invalid timestamp format: {str(e)}",
                    401,
                    request_id=request_id
                ), 401
            
            # Get message_id from body for canonical string
            try:
                json_data = request.get_json()
                message_id = json_data.get('message_id', '') if json_data else ''
            except:
                message_id = ''
            
            # Verify HMAC signature
            try:
                signature_valid = self.hmac_service.verify_signature(
                    method=request.method,
                    path=request.path,
                    timestamp=timestamp,
                    body=raw_body,
                    secret=secret,
                    provided_signature=signature,
                    message_id=message_id
                )
                
                if not signature_valid:
                    api_key.update_usage(success=False)
                    return False, self.create_error_response(
                        "unauthorized",
                        "Invalid HMAC signature",
                        401,
                        request_id=request_id
                    ), 401
            except Exception as e:
                api_key.update_usage(success=False)
                return False, self.create_error_response(
                    "unauthorized",
                    f"Signature verification failed: {str(e)}",
                    401,
                    request_id=request_id
                ), 401
            
            # Update API key usage (successful authentication)
            api_key.update_usage(success=True)
            
            # Set authentication context
            g.auth_context = {
                "organization_id": api_key.organization_id,
                "agent_id": api_key.agent_id,
                "key_id": api_key.key_id,
                "request_id": request_id,
                "api_key": api_key
            }
            
            return True, None, None  # Authentication successful
            
        except Exception as e:
            return False, self.create_error_response(
                "unauthorized",
                f"Authentication error: {str(e)}",
                401,
                request_id=request_id
            ), 401
    
    def check_idempotency(self, body_hash: str, request_id: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[int]]:
        """
        Perform Redis idempotency check.
        
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
        if hasattr(g, 'auth_context'):
            return {
                "organization_id": g.auth_context["organization_id"],
                "agent_id": g.auth_context.get("agent_id"),
                "request_id": g.auth_context["request_id"]
            }
        return None
    
    def validate_feature_flags(self) -> Dict[str, bool]:
        """
        Get current feature flag status.
        
        Returns:
            Dict with feature flag status
        """
        return {
            "per_org_keys": self.get_feature_flag("BRIKK_FEATURE_PER_ORG_KEYS"),
            "idempotency": self.get_feature_flag("BRIKK_IDEM_ENABLED"),
            "uuid4_allowed": self.get_feature_flag("BRIKK_ALLOW_UUID4")
        }
    
    def get_request_metrics(self) -> Dict[str, Any]:
        """
        Get request metrics for monitoring.
        
        Returns:
            Dict with request metrics
        """
        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "feature_flags": self.validate_feature_flags()
        }
        
        if hasattr(g, 'auth_context'):
            metrics["authenticated"] = True
            metrics["organization_id"] = g.auth_context["organization_id"]
            metrics["key_id"] = g.auth_context["key_id"]
        else:
            metrics["authenticated"] = False
        
        return metrics


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
