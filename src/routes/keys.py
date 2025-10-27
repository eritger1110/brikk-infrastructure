# -*- coding: utf-8 -*-
"""
API Key management endpoints
Part of Phase 10-12: Production-ready security
"""

from flask import Blueprint, jsonify
from datetime import datetime

from src.middleware.auth_middleware import require_api_key, get_current_api_key
from src.infra.db import db

keys_bp = Blueprint('keys', __name__, url_prefix='/keys')


@keys_bp.route('/me', methods=['GET'])
@require_api_key
def get_my_key_info():
    """
    Get information about the current API key.
    
    Returns key metadata (never the actual key).
    """
    api_key = get_current_api_key()

    if not api_key:
        return jsonify({"error": "Authentication required"}), 401

    return jsonify({
        "id": api_key.id,
        "key_id": api_key.key_id,
        "key_prefix": api_key.key_prefix,
        "name": api_key.name,
        "description": api_key.description,
        "organization_id": api_key.organization_id,
        "organization_name": api_key.organization.name if api_key.organization else None,
        "agent_id": api_key.agent_id,
        "is_active": api_key.is_active,
        "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
        "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "total_requests": api_key.total_requests,
        "failed_requests": api_key.failed_requests,
        "success_rate": api_key.get_success_rate(),
        "rate_limits": {
            "requests_per_minute": api_key.requests_per_minute,
            "requests_per_hour": api_key.requests_per_hour,
        },
        "budget_caps": {
            "soft_cap_usd": float(api_key.soft_cap_usd) if api_key.soft_cap_usd else None,
            "hard_cap_usd": float(api_key.hard_cap_usd) if api_key.hard_cap_usd else None,
        },
    }), 200


@keys_bp.route('/rotate', methods=['POST'])
@require_api_key
def rotate_key():
    """
    Rotate the current API key.
    
    Returns the new API key (only time it's visible).
    """
    api_key = get_current_api_key()

    if not api_key:
        return jsonify({"error": "Authentication required"}), 401

    # Rotate the secret
    new_secret = api_key.rotate_secret()

    return jsonify({
        "message": "API key rotated successfully",
        "old_key_prefix": api_key.key_prefix,
        "new_api_key": new_secret,
        "rotated_at": datetime.utcnow().isoformat(),
        "warning": "This is the only time you'll see the new key. Store it securely!",
    }), 200


@keys_bp.route('/disable', methods=['POST'])
@require_api_key
def disable_key():
    """
    Disable the current API key.
    
    This is a one-way operation. The key cannot be re-enabled.
    """
    api_key = get_current_api_key()

    if not api_key:
        return jsonify({"error": "Authentication required"}), 401

    # Disable the key
    api_key.disable()

    return jsonify({
        "message": "API key disabled successfully",
        "key_prefix": api_key.key_prefix,
        "disabled_at": datetime.utcnow().isoformat(),
    }), 200

