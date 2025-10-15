# -*- coding: utf-8 -*-
"""
Unified authentication middleware for Stage 5 API Gateway.

Supports multiple authentication methods in priority order:
1. API Key (brk_live_* / brk_test_*) via X-API-Key header
2. OAuth2 Bearer tokens via Authorization: Bearer <token>
3. Legacy HMAC v1 (fallback for existing integrations)

Each method populates Flask g with:
- g.auth_method: 'api_key' | 'oauth' | 'hmac'
- g.org_id: Organization UUID
- g.actor_id: Key ID, client ID, or HMAC key ID
- g.scopes: List of granted scopes
- g.tier: 'FREE' | 'PRO' | 'ENT' (for rate limiting)
"""
from functools import wraps
from typing import Optional, Tuple, Dict, Any, List
from flask import request, g, jsonify, current_app
from sqlalchemy import UUID
import uuid

from src.database import db
from src.models.api_gateway import OrgApiKey, OAuthToken
from src.models.api_key import ApiKey
from src.services.api_key_utils import APIKeyUtils
from src.services.security_enhanced import HMACSecurityService


class UnifiedAuth:
    """Unified authentication service supporting multiple auth methods."""
    
    def __init__(self):
        self.hmac_service = HMACSecurityService()
    
    def authenticate(self) -> Tuple[bool, Optional[Dict[str, Any]], int]:
        """
        Authenticate request using available methods in priority order.
        
        Returns:
            (success, error_response, status_code)
            
        On success: (True, None, 200) and populates Flask g
        On failure: (False, error_dict, status_code)
        """
        # Try Method 1: API Key
        api_key_header = request.headers.get('X-API-Key')
        if api_key_header:
            return self._authenticate_api_key(api_key_header)
        
        # Try Method 2: OAuth2 Bearer token
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
            return self._authenticate_oauth(token)
        
        # Try Method 3: Legacy HMAC (if headers present)
        if self._has_hmac_headers():
            return self._authenticate_hmac()
        
        # No authentication provided
        return False, {
            'error': 'unauthorized',
            'message': 'Authentication required. Provide X-API-Key, Bearer token, or HMAC headers.',
            'request_id': self.hmac_service.generate_request_id()
        }, 401
    
    def _authenticate_api_key(self, api_key: str) -> Tuple[bool, Optional[Dict[str, Any]], int]:
        """
        Authenticate using scoped API key.
        
        Args:
            api_key: The API key from X-API-Key header
            
        Returns:
            (success, error_response, status_code)
        """
        try:
            # Validate key format
            if not APIKeyUtils.is_valid_format(api_key):
                return False, {
                    'error': 'invalid_api_key',
                    'message': 'Invalid API key format. Expected brk_live_* or brk_test_*',
                    'request_id': self.hmac_service.generate_request_id()
                }, 401
            
            # Hash the key
            key_hash = APIKeyUtils.hash_key(api_key)
            
            # Look up key in database
            key_record = db.session.query(OrgApiKey).filter_by(
                key_hash=key_hash
            ).first()
            
            if not key_record:
                return False, {
                    'error': 'invalid_api_key',
                    'message': 'API key not found or invalid',
                    'request_id': self.hmac_service.generate_request_id()
                }, 401
            
            # Check if key is active
            if not key_record.is_active():
                return False, {
                    'error': 'api_key_revoked',
                    'message': 'API key has been revoked',
                    'request_id': self.hmac_service.generate_request_id()
                }, 401
            
            # Populate Flask g with auth context
            g.auth_method = 'api_key'
            g.org_id = key_record.org_id
            g.actor_id = str(key_record.id)
            g.scopes = key_record.scopes or []
            g.tier = key_record.tier
            g.api_key_record = key_record
            
            current_app.logger.info(
                f"API key auth success: org={g.org_id} key={g.actor_id} tier={g.tier}"
            )
            
            return True, None, 200
            
        except Exception as e:
            current_app.logger.error(f"API key authentication error: {e}")
            return False, {
                'error': 'authentication_error',
                'message': 'Authentication processing failed',
                'request_id': self.hmac_service.generate_request_id()
            }, 500
    
    def _authenticate_oauth(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], int]:
        """
        Authenticate using OAuth2 bearer token.
        
        Args:
            token: The JWT token from Authorization header
            
        Returns:
            (success, error_response, status_code)
            
        Note:
            This will be fully implemented in PR-3.
            For now, returns 401 to indicate OAuth is not yet supported.
        """
        # TODO: Implement in PR-3
        # Will verify JWT signature, check expiry, validate scopes
        return False, {
            'error': 'oauth_not_implemented',
            'message': 'OAuth2 authentication will be available in the next release',
            'request_id': self.hmac_service.generate_request_id()
        }, 501  # Not Implemented
    
    def _authenticate_hmac(self) -> Tuple[bool, Optional[Dict[str, Any]], int]:
        """
        Authenticate using legacy HMAC v1.
        
        Returns:
            (success, error_response, status_code)
            
        Note:
            This delegates to the existing HMAC authentication system.
            Maintained for backward compatibility with existing integrations.
        """
        try:
            # Extract HMAC headers
            key_id = request.headers.get('X-Brikk-Key')
            timestamp = request.headers.get('X-Brikk-Timestamp')
            signature = request.headers.get('X-Brikk-Signature')
            
            if not all([key_id, timestamp, signature]):
                return False, {
                    'error': 'missing_hmac_headers',
                    'message': 'Missing required HMAC headers',
                    'request_id': self.hmac_service.generate_request_id()
                }, 400
            
            # Validate timestamp
            timestamp_valid, timestamp_error = self.hmac_service.validate_timestamp_drift(timestamp)
            if not timestamp_valid:
                return False, {
                    'error': 'invalid_timestamp',
                    'message': timestamp_error,
                    'request_id': self.hmac_service.generate_request_id()
                }, 401
            
            # Look up legacy API key
            api_key = ApiKey.get_by_key_id(key_id)
            if not api_key or not api_key.is_valid():
                return False, {
                    'error': 'invalid_api_key',
                    'message': 'API key not found or inactive',
                    'request_id': self.hmac_service.generate_request_id()
                }, 401
            
            # Verify HMAC signature
            body = request.get_data()
            message_id = self.hmac_service.extract_message_id_from_body(body)
            secret = api_key.decrypt_secret()
            
            signature_valid = self.hmac_service.verify_signature(
                method=request.method,
                path=self.hmac_service.sanitize_path_for_signing(request.path),
                timestamp=timestamp,
                body=body,
                secret=secret,
                message_id=message_id,
                provided_signature=signature
            )
            
            if not signature_valid:
                return False, {
                    'error': 'invalid_signature',
                    'message': 'HMAC signature verification failed',
                    'request_id': self.hmac_service.generate_request_id()
                }, 401
            
            # Populate Flask g with auth context
            g.auth_method = 'hmac'
            g.org_id = uuid.UUID(api_key.organization_id) if api_key.organization_id else None
            g.actor_id = key_id
            g.scopes = ['*']  # HMAC keys have full access for backward compat
            g.tier = 'ENT'  # Legacy keys treated as enterprise tier
            g.api_key_record = api_key
            
            current_app.logger.info(
                f"HMAC auth success: org={g.org_id} key={key_id}"
            )
            
            return True, None, 200
            
        except Exception as e:
            current_app.logger.error(f"HMAC authentication error: {e}")
            return False, {
                'error': 'authentication_error',
                'message': 'Authentication processing failed',
                'request_id': self.hmac_service.generate_request_id()
            }, 500
    
    def _has_hmac_headers(self) -> bool:
        """Check if request has HMAC authentication headers."""
        return all([
            request.headers.get('X-Brikk-Key'),
            request.headers.get('X-Brikk-Timestamp'),
            request.headers.get('X-Brikk-Signature')
        ])


# Global auth instance
_auth = UnifiedAuth()


def require_auth(scopes: Optional[List[str]] = None):
    """
    Decorator to require authentication and optionally check scopes.
    
    Args:
        scopes: Optional list of required scopes. If provided, at least one must match.
                Use ['*'] to require any valid authentication.
                Use ['agents:read'] to require specific scope.
    
    Example:
        @app.route('/agents')
        @require_auth(scopes=['agents:read', 'agents:*'])
        def list_agents():
            org_id = g.org_id
            ...
    
    Populates Flask g with:
        - g.auth_method: Authentication method used
        - g.org_id: Organization UUID
        - g.actor_id: Actor identifier (key ID, client ID, etc.)
        - g.scopes: List of granted scopes
        - g.tier: Rate limit tier
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Authenticate
            success, error, status = _auth.authenticate()
            
            if not success:
                return jsonify(error), status
            
            # Check scopes if required
            if scopes:
                granted_scopes = getattr(g, 'scopes', [])
                
                # '*' in granted scopes means full access
                if '*' in granted_scopes:
                    return f(*args, **kwargs)
                
                # Check if any required scope is granted
                has_required_scope = any(
                    required_scope in granted_scopes
                    for required_scope in scopes
                )
                
                if not has_required_scope:
                    return jsonify({
                        'error': 'insufficient_scope',
                        'message': f'Required scopes: {", ".join(scopes)}',
                        'granted_scopes': granted_scopes,
                        'request_id': HMACSecurityService.generate_request_id()
                    }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def get_auth_context() -> Dict[str, Any]:
    """
    Get current authentication context from Flask g.
    
    Returns:
        Dictionary with auth_method, org_id, actor_id, scopes, tier
        
    Raises:
        RuntimeError: If called outside of authenticated request context
    """
    if not hasattr(g, 'auth_method'):
        raise RuntimeError('No authentication context available')
    
    return {
        'auth_method': g.auth_method,
        'org_id': str(g.org_id) if g.org_id else None,
        'actor_id': g.actor_id,
        'scopes': g.scopes,
        'tier': g.tier
    }

