"""
Health and readiness endpoints for the service.
"""

from flask import Blueprint, jsonify
from src.services.metrics import get_metrics_service
import time

bp = Blueprint("health", __name__)


@bp.route("/healthz", methods=["GET", "HEAD"])
def healthz():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "coordination-api",
        "timestamp": time.time(),
    })


@bp.route("/readyz", methods=["GET", "HEAD"])
def readyz():
    """Readiness check endpoint."""
    metrics_service = get_metrics_service()
    is_ready, checks = metrics_service.check_dependencies()

    if is_ready:
        return jsonify({
            "status": "ready",
            "service": "coordination-api",
            "timestamp": time.time(),
            "checks": checks,
        })

    return jsonify({
        "status": "not_ready",
        "service": "coordination-api",
        "timestamp": time.time(),
        "checks": checks,
    }), 503

