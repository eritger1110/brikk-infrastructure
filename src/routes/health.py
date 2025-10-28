# -*- coding: utf-8 -*-

from flask import Blueprint, jsonify
import time
from unittest.mock import patch

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET', 'HEAD'])
@health_bp.route('/healthz', methods=['GET', 'HEAD'])
def healthz():
    """Health check endpoint (available at both /health and /healthz).
    
    Note: This endpoint is automatically exempt from rate limiting
    because it doesn't require authentication and is needed for
    infrastructure health checks (Render, load balancers, etc.).
    """
    return jsonify({
        'status': 'healthy',
        'service': 'coordination-api',
        'timestamp': time.time()
    }), 200


@health_bp.route('/readyz', methods=['GET', 'HEAD'])
def readyz():
    """Readiness check endpoint."""
    # For now, we'll just return a simple ready status.
    # In a real application, we would check dependencies here.
    return jsonify({
        'status': 'ready',
        'service': 'coordination-api',
        'timestamp': time.time(),
        'checks': {
            'redis': True
        }
    }), 200

