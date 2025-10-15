# -*- coding: utf-8 -*-
"""
API Key management endpoints for Stage 5 API Gateway.

Allows organizations to create, list, and revoke scoped API keys.
Requires authentication (initially via admin token, later via OAuth/session).
"""
from flask import Blueprint, request, jsonify, g
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional
from datetime import datetime
import uuid

from src.database import db
from src.models.api_gateway import OrgApiKey
from src.models.org import Organization
from src.services.api_key_utils import APIKeyUtils
from src.services.security_enhanced import HMACSecurityService

# Create blueprint
api_keys_bp = Blueprint('api_keys', __name__, url_prefix='/v1/keys')


# Pydantic schemas
class CreateAPIKeyRequest(BaseModel):
    """Request schema for creating an API key."""
    name: str = Field(..., min_length=1, max_length=120, description="Human-readable key name")
    scopes: List[str] = Field(default=['*'], description="List of scopes for the key")
    tier: str = Field(default='FREE', description="Rate limit tier: FREE, PRO, or ENT")
    is_test: bool = Field(default=False, description="If true, creates test key (brk_test_*)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Production API Key",
                "scopes": ["agents:read", "agents:write", "workflows:*"],
                "tier": "PRO",
                "is_test": False
            }
        }


class APIKeyResponse(BaseModel):
    """Response schema for API key (without secret)."""
    id: str
    org_id: str
    name: str
    scopes: List[str]
    tier: str
    created_at: str
    revoked_at: Optional[str] = None
    is_active: bool
    key_prefix: str  # First 12 chars of key for identification


class APIKeyWithSecretResponse(APIKeyResponse):
    """Response schema for newly created API key (includes secret once)."""
    api_key: str  # Full key - only returned on creation


# Helper functions
def get_org_from_request() -> Optional[Organization]:
    """
    Get organization from request context.
    
    For now, requires org_id in request body or query params.
    In future PRs, this will use authenticated session/OAuth.
    """
    # Try to get from Flask g (if authenticated)
    if hasattr(g, 'org_id'):
        return db.session.query(Organization).filter_by(id=g.org_id).first()
    
    # For now, allow org_id in request (temporary - will be removed in PR-3)
    org_id = request.args.get('org_id') or request.get_json().get('org_id')
    if org_id:
        try:
            org_uuid = uuid.UUID(org_id)
            return db.session.query(Organization).filter_by(id=org_uuid).first()
        except (ValueError, AttributeError):
            return None
    
    return None


# Routes
@api_keys_bp.route('', methods=['POST'])
def create_api_key():
    """
    Create a new scoped API key.
    
    Request body:
        {
            "name": "Production Key",
            "scopes": ["agents:read", "agents:write"],
            "tier": "PRO",
            "is_test": false,
            "org_id": "uuid"  # Temporary - will use authenticated org in PR-3
        }
    
    Response:
        {
            "api_key": "brk_live_...",  # Full key - save this!
            "id": "uuid",
            "org_id": "uuid",
            "name": "Production Key",
            "scopes": ["agents:read", "agents:write"],
            "tier": "PRO",
            "created_at": "2025-10-15T19:30:00Z",
            "is_active": true,
            "key_prefix": "brk_live_abc1"
        }
    
    Note:
        The full API key is only returned once during creation.
        Store it securely - it cannot be retrieved later.
    """
    try:
        # Parse request
        data = CreateAPIKeyRequest(**request.get_json())
        
        # Get organization
        org = get_org_from_request()
        if not org:
            return jsonify({
                'error': 'organization_not_found',
                'message': 'Organization not found or not specified',
                'request_id': HMACSecurityService.generate_request_id()
            }), 404
        
        # Validate tier
        if data.tier not in ['FREE', 'PRO', 'ENT']:
            return jsonify({
                'error': 'invalid_tier',
                'message': 'Tier must be FREE, PRO, or ENT',
                'request_id': HMACSecurityService.generate_request_id()
            }), 400
        
        # Generate API key
        api_key = APIKeyUtils.generate_key(is_test=data.is_test)
        key_hash = APIKeyUtils.hash_key(api_key)
        
        # Create database record
        key_record = OrgApiKey(
            org_id=org.id,
            name=data.name,
            key_hash=key_hash,
            scopes=data.scopes,
            tier=data.tier
        )
        
        db.session.add(key_record)
        db.session.commit()
        
        # Return response with full key (only time it's shown)
        response = APIKeyWithSecretResponse(
            id=str(key_record.id),
            org_id=str(key_record.org_id),
            name=key_record.name,
            scopes=key_record.scopes,
            tier=key_record.tier,
            created_at=key_record.created_at.isoformat(),
            revoked_at=key_record.revoked_at.isoformat() if key_record.revoked_at else None,
            is_active=key_record.is_active(),
            key_prefix=api_key[:12],
            api_key=api_key
        )
        
        return jsonify(response.model_dump()), 201
        
    except ValidationError as e:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid request data',
            'details': e.errors(),
            'request_id': HMACSecurityService.generate_request_id()
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'internal_error',
            'message': f'Failed to create API key: {str(e)}',
            'request_id': HMACSecurityService.generate_request_id()
        }), 500


@api_keys_bp.route('', methods=['GET'])
def list_api_keys():
    """
    List all API keys for the authenticated organization.
    
    Query params:
        org_id: Organization UUID (temporary - will use authenticated org in PR-3)
        include_revoked: If true, includes revoked keys (default: false)
    
    Response:
        {
            "keys": [
                {
                    "id": "uuid",
                    "org_id": "uuid",
                    "name": "Production Key",
                    "scopes": ["agents:read"],
                    "tier": "PRO",
                    "created_at": "2025-10-15T19:30:00Z",
                    "revoked_at": null,
                    "is_active": true,
                    "key_prefix": "brk_live_abc1"
                }
            ],
            "total": 1
        }
    """
    try:
        # Get organization
        org = get_org_from_request()
        if not org:
            return jsonify({
                'error': 'organization_not_found',
                'message': 'Organization not found or not specified',
                'request_id': HMACSecurityService.generate_request_id()
            }), 404
        
        # Query keys
        query = db.session.query(OrgApiKey).filter_by(org_id=org.id)
        
        # Filter by active status
        include_revoked = request.args.get('include_revoked', 'false').lower() == 'true'
        if not include_revoked:
            query = query.filter(OrgApiKey.revoked_at.is_(None))
        
        keys = query.order_by(OrgApiKey.created_at.desc()).all()
        
        # Build response
        key_responses = []
        for key in keys:
            # We don't have the original key, so we can't show prefix
            # Instead, show first 8 chars of the hash
            key_responses.append(APIKeyResponse(
                id=str(key.id),
                org_id=str(key.org_id),
                name=key.name,
                scopes=key.scopes,
                tier=key.tier,
                created_at=key.created_at.isoformat(),
                revoked_at=key.revoked_at.isoformat() if key.revoked_at else None,
                is_active=key.is_active(),
                key_prefix=key.key_hash[:12]  # Show hash prefix for identification
            ).model_dump())
        
        return jsonify({
            'keys': key_responses,
            'total': len(key_responses)
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'internal_error',
            'message': f'Failed to list API keys: {str(e)}',
            'request_id': HMACSecurityService.generate_request_id()
        }), 500


@api_keys_bp.route('/<key_id>', methods=['DELETE'])
def revoke_api_key(key_id):
    """
    Revoke an API key.
    
    Path params:
        key_id: UUID of the key to revoke
    
    Query params:
        org_id: Organization UUID (temporary - will use authenticated org in PR-3)
    
    Response:
        {
            "message": "API key revoked successfully",
            "key_id": "uuid",
            "revoked_at": "2025-10-15T19:35:00Z"
        }
    """
    try:
        # Get organization
        org = get_org_from_request()
        if not org:
            return jsonify({
                'error': 'organization_not_found',
                'message': 'Organization not found or not specified',
                'request_id': HMACSecurityService.generate_request_id()
            }), 404
        
        # Parse key_id
        try:
            key_uuid = uuid.UUID(key_id)
        except ValueError:
            return jsonify({
                'error': 'invalid_key_id',
                'message': 'Invalid key ID format',
                'request_id': HMACSecurityService.generate_request_id()
            }), 400
        
        # Find key
        key = db.session.query(OrgApiKey).filter_by(
            id=key_uuid,
            org_id=org.id
        ).first()
        
        if not key:
            return jsonify({
                'error': 'key_not_found',
                'message': 'API key not found',
                'request_id': HMACSecurityService.generate_request_id()
            }), 404
        
        # Revoke key
        key.revoked_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'API key revoked successfully',
            'key_id': str(key.id),
            'revoked_at': key.revoked_at.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'internal_error',
            'message': f'Failed to revoke API key: {str(e)}',
            'request_id': HMACSecurityService.generate_request_id()
        }), 500


@api_keys_bp.route('/<key_id>', methods=['GET'])
def get_api_key(key_id):
    """
    Get details of a specific API key.
    
    Path params:
        key_id: UUID of the key
    
    Query params:
        org_id: Organization UUID (temporary - will use authenticated org in PR-3)
    
    Response:
        {
            "id": "uuid",
            "org_id": "uuid",
            "name": "Production Key",
            "scopes": ["agents:read"],
            "tier": "PRO",
            "created_at": "2025-10-15T19:30:00Z",
            "revoked_at": null,
            "is_active": true,
            "key_prefix": "brk_live_abc1"
        }
    """
    try:
        # Get organization
        org = get_org_from_request()
        if not org:
            return jsonify({
                'error': 'organization_not_found',
                'message': 'Organization not found or not specified',
                'request_id': HMACSecurityService.generate_request_id()
            }), 404
        
        # Parse key_id
        try:
            key_uuid = uuid.UUID(key_id)
        except ValueError:
            return jsonify({
                'error': 'invalid_key_id',
                'message': 'Invalid key ID format',
                'request_id': HMACSecurityService.generate_request_id()
            }), 400
        
        # Find key
        key = db.session.query(OrgApiKey).filter_by(
            id=key_uuid,
            org_id=org.id
        ).first()
        
        if not key:
            return jsonify({
                'error': 'key_not_found',
                'message': 'API key not found',
                'request_id': HMACSecurityService.generate_request_id()
            }), 404
        
        # Build response
        response = APIKeyResponse(
            id=str(key.id),
            org_id=str(key.org_id),
            name=key.name,
            scopes=key.scopes,
            tier=key.tier,
            created_at=key.created_at.isoformat(),
            revoked_at=key.revoked_at.isoformat() if key.revoked_at else None,
            is_active=key.is_active(),
            key_prefix=key.key_hash[:12]
        )
        
        return jsonify(response.model_dump()), 200
        
    except Exception as e:
        return jsonify({
            'error': 'internal_error',
            'message': f'Failed to get API key: {str(e)}',
            'request_id': HMACSecurityService.generate_request_id()
        }), 500

