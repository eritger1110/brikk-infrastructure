# -*- coding: utf-8 -*-
"""
OAuth2 Routes - Client Credentials Flow.

Implements OAuth2 client management and token endpoints.
Supports the client_credentials grant type for machine-to-machine authentication.
"""
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from src.database import db
from src.models.api_gateway import OAuthClient
from src.services.oauth2 import (
    generate_client_credentials,
    generate_client_secret,
    verify_client_secret,
    create_token_record
)

# Create blueprint
oauth_bp = Blueprint('oauth', __name__)


@oauth_bp.route('/token', methods=['POST'])
def token_endpoint():
    """
    OAuth2 Token Endpoint - Client Credentials Grant.
    
    Request (application/x-www-form-urlencoded or JSON):
        {
            "grant_type": "client_credentials",
            "client_id": "cli_abc123",
            "client_secret": "cs_live_...",
            "scope": "agents:read workflows:*"  # Optional, space-separated
        }
    
    Response (200 OK):
        {
            "access_token": "eyJ...",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "agents:read workflows:*"
        }
    
    Errors:
        400 - Invalid request (missing fields)
        401 - Invalid client credentials
        501 - Unsupported grant type
    """
    # Parse request (support both form and JSON)
    if request.content_type == 'application/x-www-form-urlencoded':
        data = request.form.to_dict()
    else:
        data = request.get_json(silent=True) or {}
    
    grant_type = data.get('grant_type')
    client_id = data.get('client_id')
    client_secret = data.get('client_secret')
    requested_scope = data.get('scope', '')
    
    # Validate required fields
    if not grant_type or not client_id or not client_secret:
        return jsonify({
            'error': 'invalid_request',
            'error_description': 'Missing required fields: grant_type, client_id, client_secret'
        }), 400
    
    # Only support client_credentials grant
    if grant_type != 'client_credentials':
        return jsonify({
            'error': 'unsupported_grant_type',
            'error_description': f'Grant type {grant_type} is not supported. Use client_credentials.'
        }), 501
    
    # Look up client
    client = db.session.query(OAuthClient).filter(
        OAuthClient.client_id == client_id,
        OAuthClient.is_active == True
    ).first()
    
    if not client:
        return jsonify({
            'error': 'invalid_client',
            'error_description': 'Client not found or inactive'
        }), 401
    
    # Verify client secret
    if not verify_client_secret(client_secret, client.client_secret_hash):
        return jsonify({
            'error': 'invalid_client',
            'error_description': 'Invalid client secret'
        }), 401
    
    # Parse requested scopes
    requested_scopes = [s.strip() for s in requested_scope.split() if s.strip()]
    
    # If no scopes requested, use client's default scopes
    if not requested_scopes:
        granted_scopes = client.scopes
    else:
        # Validate requested scopes against client's allowed scopes
        granted_scopes = []
        for scope in requested_scopes:
            if scope in client.scopes or '*' in client.scopes:
                granted_scopes.append(scope)
        
        if not granted_scopes:
            return jsonify({
                'error': 'invalid_scope',
                'error_description': f'Requested scopes not allowed for this client'
            }), 400
    
    # Generate access token
    expiration_minutes = 60  # 1 hour
    access_token = generate_client_credentials(
        client_id=client.client_id,
        org_id=str(client.org_id),
        scopes=granted_scopes,
        expiration_minutes=expiration_minutes
    )
    
    # Decode token to get JTI and expiration
    from jose import jwt
    payload = jwt.decode(access_token, options={"verify_signature": False})
    jti = payload.get('jti')
    exp = payload.get('exp')
    expires_at = datetime.utcfromtimestamp(exp) if exp else datetime.utcnow() + timedelta(minutes=expiration_minutes)
    
    # Record token for revocation tracking
    create_token_record(
        client_id=client.client_id,
        jti=jti,
        expires_at=expires_at,
        scopes=granted_scopes
    )
    
    # Update client last_used_at
    client.last_used_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': expiration_minutes * 60,  # seconds
        'scope': ' '.join(granted_scopes)
    }), 200


@oauth_bp.route('/clients', methods=['POST'])
def create_client():
    """
    Create a new OAuth2 client.
    
    Request (requires authentication - will use unified auth in final version):
        {
            "name": "My Application",
            "description": "Optional description",
            "scopes": ["agents:read", "workflows:*"],
            "org_id": "uuid"  # Temporary - will use authenticated org
        }
    
    Response (201 Created):
        {
            "client_id": "cli_abc123",
            "client_secret": "cs_live_...",  # ONLY SHOWN ONCE
            "name": "My Application",
            "description": "...",
            "scopes": ["agents:read", "workflows:*"],
            "org_id": "uuid",
            "created_at": "2025-10-15T19:30:00Z",
            "is_active": true
        }
    """
    data = request.get_json(silent=True) or {}
    
    # Validate required fields
    name = data.get('name', '').strip()
    org_id = data.get('org_id', '').strip()
    scopes = data.get('scopes', [])
    
    if not name or not org_id:
        return jsonify({
            'error': 'validation_error',
            'message': 'name and org_id are required'
        }), 400
    
    if not isinstance(scopes, list) or not scopes:
        return jsonify({
            'error': 'validation_error',
            'message': 'scopes must be a non-empty list'
        }), 400
    
    # Generate client credentials
    client_id = f"cli_{uuid.uuid4().hex[:16]}"
    client_secret, client_secret_hash = generate_client_secret()
    
    # Create client
    client = OAuthClient(
        client_id=client_id,
        client_secret_hash=client_secret_hash,
        name=name,
        description=data.get('description'),
        org_id=uuid.UUID(org_id),
        scopes=scopes,
        is_active=True
    )
    
    try:
        db.session.add(client)
        db.session.commit()
        
        return jsonify({
            'client_id': client.client_id,
            'client_secret': client_secret,  # ONLY SHOWN ONCE
            'name': client.name,
            'description': client.description,
            'scopes': client.scopes,
            'org_id': str(client.org_id),
            'created_at': client.created_at.isoformat() + 'Z',
            'is_active': client.is_active,
            'warning': 'Save the client_secret now - it will not be shown again'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'internal_error',
            'message': 'Failed to create client'
        }), 500


@oauth_bp.route('/clients', methods=['GET'])
def list_clients():
    """
    List OAuth2 clients for an organization.
    
    Query params:
        org_id: Organization UUID (temporary - will use authenticated org)
    
    Response (200 OK):
        {
            "clients": [
                {
                    "client_id": "cli_abc123",
                    "name": "My Application",
                    "description": "...",
                    "scopes": ["agents:read"],
                    "created_at": "2025-10-15T19:30:00Z",
                    "last_used_at": "2025-10-15T20:00:00Z",
                    "is_active": true
                }
            ]
        }
    """
    org_id = request.args.get('org_id')
    
    if not org_id:
        return jsonify({
            'error': 'validation_error',
            'message': 'org_id query parameter is required'
        }), 400
    
    try:
        clients = db.session.query(OAuthClient).filter(
            OAuthClient.org_id == uuid.UUID(org_id)
        ).order_by(OAuthClient.created_at.desc()).all()
        
        return jsonify({
            'clients': [
                {
                    'client_id': c.client_id,
                    'name': c.name,
                    'description': c.description,
                    'scopes': c.scopes,
                    'created_at': c.created_at.isoformat() + 'Z',
                    'last_used_at': c.last_used_at.isoformat() + 'Z' if c.last_used_at else None,
                    'is_active': c.is_active
                }
                for c in clients
            ]
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'internal_error',
            'message': 'Failed to list clients'
        }), 500


@oauth_bp.route('/clients/<client_id>', methods=['DELETE'])
def revoke_client(client_id: str):
    """
    Revoke (deactivate) an OAuth2 client.
    
    This prevents the client from obtaining new tokens.
    Existing tokens remain valid until they expire.
    
    Response (200 OK):
        {
            "message": "Client revoked successfully",
            "client_id": "cli_abc123"
        }
    """
    client = db.session.query(OAuthClient).filter(
        OAuthClient.client_id == client_id
    ).first()
    
    if not client:
        return jsonify({
            'error': 'not_found',
            'message': 'Client not found'
        }), 404
    
    try:
        client.is_active = False
        db.session.commit()
        
        return jsonify({
            'message': 'Client revoked successfully',
            'client_id': client.client_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'internal_error',
            'message': 'Failed to revoke client'
        }), 500

