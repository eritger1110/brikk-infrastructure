"""
Feature Flags API Routes

Provides API endpoints for managing and querying feature flags.
"""

from flask import Blueprint, jsonify, request
from src.utils.feature_flags import get_all_flags, set_flag, FeatureFlag
from src.infra.log import get_logger

logger = get_logger(__name__)

feature_flags_bp = Blueprint("feature_flags", __name__, url_prefix="/api/v1/feature-flags")


@feature_flags_bp.route("", methods=["GET"])
def list_feature_flags():
    """
    Get all feature flags and their current states.
    
    Returns:
        JSON response with all feature flags
    """
    try:
        flags = get_all_flags()
        return jsonify({
            "success": True,
            "flags": flags,
            "count": len(flags)
        }), 200
    except Exception as e:
        logger.error(f"Failed to get feature flags: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to retrieve feature flags"
        }), 500


@feature_flags_bp.route("/<flag_name>", methods=["GET"])
def get_feature_flag(flag_name: str):
    """
    Get a specific feature flag value.
    
    Args:
        flag_name: Name of the feature flag
        
    Returns:
        JSON response with flag value
    """
    try:
        # Validate flag name
        try:
            flag = FeatureFlag(flag_name)
        except ValueError:
            return jsonify({
                "success": False,
                "error": f"Unknown feature flag: {flag_name}"
            }), 404
        
        from src.utils.feature_flags import is_enabled
        enabled = is_enabled(flag)
        
        return jsonify({
            "success": True,
            "flag": flag_name,
            "enabled": enabled
        }), 200
    except Exception as e:
        logger.error(f"Failed to get feature flag {flag_name}: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to retrieve feature flag"
        }), 500


@feature_flags_bp.route("/<flag_name>", methods=["PUT"])
def update_feature_flag(flag_name: str):
    """
    Update a feature flag value.
    
    Request body:
        {
            "enabled": true|false,
            "ttl": 3600  # optional, seconds
        }
    
    Args:
        flag_name: Name of the feature flag
        
    Returns:
        JSON response with update status
    """
    try:
        # Validate flag name
        try:
            flag = FeatureFlag(flag_name)
        except ValueError:
            return jsonify({
                "success": False,
                "error": f"Unknown feature flag: {flag_name}"
            }), 404
        
        # Get request data
        data = request.get_json()
        if not data or "enabled" not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'enabled' field in request body"
            }), 400
        
        enabled = data["enabled"]
        ttl = data.get("ttl")
        
        # Update flag
        success = set_flag(flag, enabled, ttl)
        
        if success:
            return jsonify({
                "success": True,
                "flag": flag_name,
                "enabled": enabled,
                "ttl": ttl
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to update feature flag (Redis not configured?)"
            }), 500
    except Exception as e:
        logger.error(f"Failed to update feature flag {flag_name}: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to update feature flag"
        }), 500

