# -*- coding: utf-8 -*-
"""
Test routes for unified authentication system.

Demonstrates scope-based authorization with API keys, OAuth, and HMAC.
These routes are for testing PR-2 functionality.
"""
from flask import Blueprint, jsonify, g
from src.services.unified_auth import require_auth, get_auth_context

# Create blueprint
auth_test_bp = Blueprint('auth_test', __name__)


@auth_test_bp.route('/public', methods=['GET'])
def public_endpoint():
    """
    Public endpoint - no authentication required.
    
    Response:
        {
            "message": "This endpoint is public",
            "authenticated": false
        }
    """
    return jsonify({
        'message': 'This endpoint is public',
        'authenticated': False
    }), 200


@auth_test_bp.route('/authenticated', methods=['GET'])
@require_auth(scopes=['*'])
def authenticated_endpoint():
    """
    Authenticated endpoint - requires any valid authentication.
    
    Headers:
        X-API-Key: brk_live_* or brk_test_*
        OR
        Authorization: Bearer <token>
        OR
        X-Brikk-Key, X-Brikk-Timestamp, X-Brikk-Signature (HMAC)
    
    Response:
        {
            "message": "You are authenticated",
            "auth_method": "api_key|oauth|hmac",
            "org_id": "uuid",
            "actor_id": "key_id|client_id|hmac_key_id",
            "scopes": ["list", "of", "scopes"],
            "tier": "FREE|PRO|ENT"
        }
    """
    context = get_auth_context()
    return jsonify({
        'message': 'You are authenticated',
        **context
    }), 200


@auth_test_bp.route('/agents-read', methods=['GET'])
@require_auth(scopes=['agents:read', 'agents:*', '*'])
def agents_read_endpoint():
    """
    Scoped endpoint - requires agents:read or agents:* or * scope.
    
    Headers:
        X-API-Key: brk_live_* (with agents:read scope)
    
    Response:
        {
            "message": "You have agents:read permission",
            "auth_method": "api_key",
            "org_id": "uuid",
            "scopes": ["agents:read", "workflows:read"]
        }
    
    Error (403):
        {
            "error": "insufficient_scope",
            "message": "Required scopes: agents:read, agents:*, *",
            "granted_scopes": ["workflows:read"],
            "request_id": "..."
        }
    """
    context = get_auth_context()
    return jsonify({
        'message': 'You have agents:read permission',
        'auth_method': context['auth_method'],
        'org_id': context['org_id'],
        'scopes': context['scopes']
    }), 200


@auth_test_bp.route('/agents-write', methods=['POST'])
@require_auth(scopes=['agents:write', 'agents:*', '*'])
def agents_write_endpoint():
    """
    Scoped endpoint - requires agents:write or agents:* or * scope.
    
    Headers:
        X-API-Key: brk_live_* (with agents:write scope)
    
    Response:
        {
            "message": "You have agents:write permission",
            "auth_method": "api_key",
            "org_id": "uuid",
            "scopes": ["agents:write"]
        }
    """
    context = get_auth_context()
    return jsonify({
        'message': 'You have agents:write permission',
        'auth_method': context['auth_method'],
        'org_id': context['org_id'],
        'scopes': context['scopes']
    }), 200


@auth_test_bp.route('/admin', methods=['GET'])
@require_auth(scopes=['admin:*', '*'])
def admin_endpoint():
    """
    Admin-only endpoint - requires admin:* or * scope.
    
    Most keys won't have this scope, so this demonstrates 403 responses.
    
    Headers:
        X-API-Key: brk_live_* (with admin:* scope)
    
    Response:
        {
            "message": "You have admin access",
            "auth_method": "api_key",
            "org_id": "uuid",
            "scopes": ["admin:*"]
        }
    """
    context = get_auth_context()
    return jsonify({
        'message': 'You have admin access',
        'auth_method': context['auth_method'],
        'org_id': context['org_id'],
        'scopes': context['scopes']
    }), 200

