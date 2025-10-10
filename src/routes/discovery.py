"""
Discovery Routes

Provides API endpoints for agent service discovery and registration.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from src.services.discovery_service import DiscoveryService
from src.database.db import db
from src.services.structured_logging import get_logger

logger = get_logger("brikk.discovery.routes")

discovery_bp = Blueprint("discovery", __name__)

@discovery_bp.route("/api/v1/discovery/register", methods=["POST"])
@jwt_required()
def register_service():
    """Register a new agent service"""
    try:
        data = request.get_json()
        claims = get_jwt()
        agent_id = claims.get("agent_id") # Assuming agent identity is in JWT
        
        if not data or not all(k in data for k in ["service_name", "service_url", "capabilities"]):
            return jsonify({"error": "Missing required fields"}), 400
            
        discovery_service = DiscoveryService(db.session)
        service = discovery_service.register_service(
            agent_id=agent_id,
            service_name=data["service_name"],
            service_url=data["service_url"],
            capabilities=data["capabilities"]
        )
        
        return jsonify({"id": service.id, "name": service.name}), 201
        
    except Exception as e:
        logger.error(f"Failed to register service: {e}")
        return jsonify({"error": "Failed to register service"}), 500

@discovery_bp.route("/api/v1/discovery/discover", methods=["GET"])
@jwt_required()
def discover_services():
    """Discover available agent services"""
    try:
        capability = request.args.get("capability")
        claims = get_jwt()
        organization_id = claims.get("organization_id")
        
        discovery_service = DiscoveryService(db.session)
        services = discovery_service.discover_services(capability, organization_id)
        
        return jsonify(services), 200
        
    except Exception as e:
        logger.error(f"Failed to discover services: {e}")
        return jsonify({"error": "Failed to discover services"}), 500

@discovery_bp.route("/api/v1/discovery/services/<int:service_id>", methods=["GET"])
@jwt_required()
def get_service_details(service_id: int):
    """Get details of a specific service"""
    try:
        discovery_service = DiscoveryService(db.session)
        service = discovery_service.get_service_details(service_id)
        
        if not service:
            return jsonify({"error": "Service not found or has expired"}), 404
            
        return jsonify(service), 200
        
    except Exception as e:
        logger.error(f"Failed to get service details for {service_id}: {e}")
        return jsonify({"error": "Failed to retrieve service details"}), 500

@discovery_bp.route("/api/v1/discovery/services/<int:service_id>/heartbeat", methods=["POST"])
@jwt_required()
def service_heartbeat(service_id: int):
    """Send a heartbeat to keep a service registration alive"""
    try:
        discovery_service = DiscoveryService(db.session)
        success = discovery_service.heartbeat(service_id)
        
        if success:
            return jsonify({"message": "Heartbeat received"}), 200
        else:
            return jsonify({"error": "Service not found"}), 404
            
    except Exception as e:
        logger.error(f"Failed to process heartbeat for service {service_id}: {e}")
        return jsonify({"error": "Failed to process heartbeat"}), 500

@discovery_bp.route("/api/v1/discovery/cleanup", methods=["POST"])
@jwt_required() # Should be restricted to admin users
def cleanup_expired_services():
    """Manually trigger cleanup of expired services"""
    try:
        claims = get_jwt()
        # Add role-based access control here to ensure only admins can run this
        
        discovery_service = DiscoveryService(db.session)
        removed_count = discovery_service.remove_expired_services()
        
        return jsonify({"message": f"Removed {removed_count} expired services"}), 200
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired services: {e}")
        return jsonify({"error": "Failed to cleanup services"}), 500

