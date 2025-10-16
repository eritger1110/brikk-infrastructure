# -*- coding: utf-8 -*-
"""
Deprecation Information Endpoint (Phase 6 PR-M).

Provides public endpoint to list all deprecated features.
"""
from flask import Blueprint, jsonify
from src.services.deprecation import get_deprecations, days_until_sunset

deprecations_bp = Blueprint('deprecations', __name__)


@deprecations_bp.route('/deprecations', methods=['GET'])
def list_deprecations():
    """
    List all deprecated API endpoints and features.
    
    Returns:
        JSON object with deprecated endpoints and their details
    """
    deprecations = get_deprecations()
    
    # Enhance with calculated fields
    enhanced = {}
    for endpoint, info in deprecations.items():
        enhanced[endpoint] = {
            **info,
            'days_until_sunset': days_until_sunset(endpoint)
        }
    
    return jsonify({
        'deprecations': enhanced,
        'count': len(enhanced),
        'message': 'Check X-API-Deprecated headers in responses for real-time warnings'
    }), 200

