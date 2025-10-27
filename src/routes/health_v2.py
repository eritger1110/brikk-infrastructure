# -*- coding: utf-8 -*-
"""
Enhanced health check endpoints
Part of Phase 10-12: Production-ready observability
"""

from flask import Blueprint, jsonify
from datetime import datetime
import os

from src.services.circuit_breaker import get_all_circuit_states
from src.infra.db import db

health_v2_bp = Blueprint('health_v2', __name__, url_prefix='/v2/health')


@health_v2_bp.route('/status', methods=['GET'])
def get_status():
    """
    Get comprehensive system status.
    
    Returns service health, database connectivity, and circuit breaker states.
    """
    status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv('APP_VERSION', 'unknown'),
        "environment": os.getenv('FLASK_ENV', 'production'),
    }

    # Check database connectivity
    try:
        db.session.execute(db.text('SELECT 1'))
        status["database"] = "connected"
    except Exception as e:
        status["database"] = "disconnected"
        status["database_error"] = str(e)
        status["status"] = "degraded"

    # Get circuit breaker states
    circuit_states = get_all_circuit_states()
    status["circuit_breakers"] = circuit_states

    # Check if any circuit is open
    if any(cb['state'] == 'open' for cb in circuit_states.values()):
        status["status"] = "degraded"

    return jsonify(status), 200


@health_v2_bp.route('/providers', methods=['GET'])
def get_provider_status():
    """
    Get provider availability status.
    
    Returns which providers are configured and their circuit breaker states.
    """
    providers = {}

    # Check OpenAI
    openai_key = os.getenv('OPENAI_API_KEY')
    providers['openai'] = {
        "configured": bool(openai_key),
        "model": os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
    }

    # Check Mistral
    mistral_key = os.getenv('MISTRAL_API_KEY')
    providers['mistral'] = {
        "configured": bool(mistral_key),
        "model": os.getenv('MISTRAL_MODEL', 'mistral-small-latest'),
    }

    # Add circuit breaker states
    circuit_states = get_all_circuit_states()
    for provider_name, provider_info in providers.items():
        circuit_key = f"{provider_name}_circuit"
        if circuit_key in circuit_states:
            provider_info["circuit_breaker"] = circuit_states[circuit_key]

    return jsonify({
        "providers": providers,
        "timestamp": datetime.utcnow().isoformat(),
    }), 200


@health_v2_bp.route('/ready', methods=['GET'])
def readiness_check():
    """
    Kubernetes-style readiness check.
    
    Returns 200 if service is ready to accept traffic, 503 otherwise.
    """
    try:
        # Check database
        db.session.execute(db.text('SELECT 1'))

        # Check at least one provider is configured
        openai_configured = bool(os.getenv('OPENAI_API_KEY'))
        mistral_configured = bool(os.getenv('MISTRAL_API_KEY'))

        if not (openai_configured or mistral_configured):
            return jsonify({
                "ready": False,
                "reason": "No providers configured"
            }), 503

        return jsonify({"ready": True}), 200

    except Exception as e:
        return jsonify({
            "ready": False,
            "reason": str(e)
        }), 503


@health_v2_bp.route('/live', methods=['GET'])
def liveness_check():
    """
    Kubernetes-style liveness check.
    
    Returns 200 if service is alive, 503 if it should be restarted.
    """
    return jsonify({"alive": True}), 200

