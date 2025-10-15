# -*- coding: utf-8 -*-
"""
OAuth2 Service for Client Credentials Flow.

Implements JWT token generation and verification using python-jose.
Supports the client_credentials grant type for machine-to-machine authentication.
"""
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from jose import jwt, JWTError
from flask import current_app

# JWT Configuration
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60  # 1 hour default
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(32)


def generate_client_credentials(
    client_id: str,
    org_id: str,
    scopes: List[str],
    expiration_minutes: Optional[int] = None
) -> str:
    """
    Generate a JWT access token for client credentials flow.
    
    Args:
        client_id: OAuth client identifier
        org_id: Organization UUID
        scopes: List of granted scopes
        expiration_minutes: Token lifetime (default: 60 minutes)
    
    Returns:
        JWT access token string
    
    Example:
        token = generate_client_credentials(
            client_id="cli_abc123",
            org_id="uuid",
            scopes=["agents:read", "workflows:*"]
        )
    """
    exp_minutes = expiration_minutes or JWT_EXPIRATION_MINUTES
    now = datetime.utcnow()
    
    payload = {
        "iss": "brikk-api-gateway",  # Issuer
        "sub": client_id,  # Subject (client_id)
        "aud": "brikk-api",  # Audience
        "exp": now + timedelta(minutes=exp_minutes),  # Expiration
        "iat": now,  # Issued at
        "nbf": now,  # Not before
        "jti": secrets.token_urlsafe(16),  # JWT ID (unique token identifier)
        "org_id": org_id,
        "scopes": scopes,
        "token_type": "access_token",
        "grant_type": "client_credentials"
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT access token.
    
    Args:
        token: JWT access token string
    
    Returns:
        Decoded token payload if valid, None if invalid
    
    Raises:
        None - returns None on any error
    
    Example:
        payload = verify_access_token(token)
        if payload:
            client_id = payload["sub"]
            org_id = payload["org_id"]
            scopes = payload["scopes"]
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            audience="brikk-api"
        )
        
        # Validate required fields
        required_fields = ["sub", "org_id", "scopes", "token_type"]
        if not all(field in payload for field in required_fields):
            return None
        
        # Validate token type
        if payload.get("token_type") != "access_token":
            return None
        
        return payload
        
    except JWTError:
        return None
    except Exception:
        return None


def generate_client_secret() -> tuple[str, str]:
    """
    Generate a client secret for OAuth2 client credentials.
    
    Returns:
        Tuple of (plain_secret, hashed_secret)
        - plain_secret: Show to user once (cs_live_... or cs_test_...)
        - hashed_secret: Store in database
    
    Example:
        plain, hashed = generate_client_secret()
        # Show plain to user: "cs_live_a1b2c3..."
        # Store hashed in database
    """
    from src.services.api_key_utils import hash_api_key
    
    # Generate 256-bit random secret
    random_bytes = secrets.token_bytes(32)
    hex_secret = random_bytes.hex()
    
    # Format with prefix
    plain_secret = f"cs_live_{hex_secret}"
    
    # Hash for storage
    hashed_secret = hash_api_key(plain_secret)
    
    return plain_secret, hashed_secret


def verify_client_secret(plain_secret: str, hashed_secret: str) -> bool:
    """
    Verify a client secret against its hash.
    
    Args:
        plain_secret: Plain text secret from request
        hashed_secret: Hashed secret from database
    
    Returns:
        True if secret matches, False otherwise
    
    Example:
        if verify_client_secret(provided_secret, stored_hash):
            # Grant access
    """
    from src.services.api_key_utils import verify_api_key
    return verify_api_key(plain_secret, hashed_secret)


def revoke_token(jti: str) -> bool:
    """
    Revoke a token by adding its JTI to the revocation list.
    
    Args:
        jti: JWT ID from token payload
    
    Returns:
        True if revoked successfully
    
    Note:
        This implementation uses the database oauth_tokens table.
        In production, consider using Redis for faster lookups.
    
    Example:
        payload = verify_access_token(token)
        if payload:
            revoke_token(payload["jti"])
    """
    from src.database import db
    from src.models.api_gateway import OAuthToken
    
    try:
        # Find token by JTI
        token_record = db.session.query(OAuthToken).filter(
            OAuthToken.jti == jti
        ).first()
        
        if token_record:
            token_record.revoked_at = datetime.utcnow()
            token_record.is_active = False
            db.session.commit()
            return True
        
        return False
        
    except Exception:
        db.session.rollback()
        return False


def is_token_revoked(jti: str) -> bool:
    """
    Check if a token has been revoked.
    
    Args:
        jti: JWT ID from token payload
    
    Returns:
        True if token is revoked, False otherwise
    
    Example:
        payload = verify_access_token(token)
        if payload and not is_token_revoked(payload["jti"]):
            # Token is valid and not revoked
    """
    from src.database import db
    from src.models.api_gateway import OAuthToken
    
    try:
        token_record = db.session.query(OAuthToken).filter(
            OAuthToken.jti == jti
        ).first()
        
        if token_record:
            return not token_record.is_active or token_record.revoked_at is not None
        
        # If token not in database, it's not revoked (stateless JWT)
        return False
        
    except Exception:
        # On error, assume not revoked (fail open for stateless JWTs)
        return False


def create_token_record(
    client_id: str,
    jti: str,
    expires_at: datetime,
    scopes: List[str]
) -> None:
    """
    Create a token record in the database for tracking and revocation.
    
    Args:
        client_id: OAuth client identifier
        jti: JWT ID (unique token identifier)
        expires_at: Token expiration timestamp
        scopes: List of granted scopes
    
    Note:
        This is optional - JWTs can be stateless. Recording tokens
        enables revocation and audit logging.
    """
    from src.database import db
    from src.models.api_gateway import OAuthToken, OAuthClient
    
    try:
        # Get client to get org_id
        client = db.session.query(OAuthClient).filter(
            OAuthClient.client_id == client_id
        ).first()
        
        if not client:
            return
        
        token = OAuthToken(
            client_id=client.id,
            jti=jti,
            expires_at=expires_at,
            scopes=scopes,
            is_active=True
        )
        
        db.session.add(token)
        db.session.commit()
        
    except Exception:
        db.session.rollback()

