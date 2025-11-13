# -*- coding: utf-8 -*-
"""
Auth0 JWT token verification utility
Verifies Auth0 access tokens using JWKS
"""
import os
import jwt
from jwt import PyJWKClient
from typing import Dict, Any, Optional
from functools import lru_cache


@lru_cache(maxsize=1)
def get_jwks_client() -> PyJWKClient:
    """
    Get JWKS client for Auth0 token verification
    Cached to avoid repeated requests
    """
    auth0_domain = os.getenv("AUTH0_DOMAIN", "brikk-dashboard.us.auth0.com")
    jwks_url = f"https://{auth0_domain}/.well-known/jwks.json"
    return PyJWKClient(jwks_url)


def verify_auth0_token(token: str) -> Dict[str, Any]:
    """
    Verify Auth0 JWT token and return decoded payload
    
    Args:
        token: JWT access token from Auth0
        
    Returns:
        Decoded token payload
        
    Raises:
        jwt.InvalidTokenError: If token is invalid
        jwt.ExpiredSignatureError: If token is expired
        Exception: For other verification errors
    """
    auth0_domain = os.getenv("AUTH0_DOMAIN", "brikk-dashboard.us.auth0.com")
    auth0_audience = os.getenv("AUTH0_AUDIENCE", "https://api.getbrikk.com")
    
    try:
        # Get signing key from JWKS
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Verify and decode token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=auth0_audience,
            issuer=f"https://{auth0_domain}/"
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise jwt.ExpiredSignatureError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise Exception(f"Token verification failed: {str(e)}")


def get_user_info_from_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Extract user information from Auth0 token
    
    Args:
        token: JWT access token from Auth0
        
    Returns:
        Dictionary with user info (sub, email, name, picture) or None if invalid
    """
    try:
        payload = verify_auth0_token(token)
        
        # Extract user info from standard and custom claims
        return {
            "sub": payload.get("sub"),
            "email": payload.get("email") or payload.get("https://api.getbrikk.com/email"),
            "name": payload.get("name") or payload.get("https://api.getbrikk.com/name"),
            "picture": payload.get("picture") or payload.get("https://api.getbrikk.com/picture"),
            "email_verified": payload.get("email_verified", False),
        }
    except Exception:
        return None
