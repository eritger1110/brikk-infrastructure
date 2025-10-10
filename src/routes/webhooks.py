"""
Webhook Routes

Provides API endpoints for managing webhook subscriptions and viewing event history.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from src.services.webhook_service import WebhookService
from src.database.db import db
from src.models.webhook import WebhookEvent
from src.services.structured_logging import get_logger

logger = get_logger("brikk.webhooks.routes")

webhooks_bp = Blueprint("webhooks", __name__)

@webhooks_bp.route("/api/v1/webhooks", methods=["POST"])
@jwt_required()
def create_webhook():
    """Create a new webhook subscription"""
    try:
        data = request.get_json()
        claims = get_jwt()
        organization_id = claims.get("organization_id")
        
        if not data or not all(k in data for k in ["url", "secret", "events"]):
            return jsonify({"error": "Missing required fields: url, secret, events"}), 400
        
        webhook_service = WebhookService(db.session)
        
        webhook = webhook_service.create_webhook(
            organization_id=organization_id,
            url=data["url"],
            secret=data["secret"],
            events=data["events"],
            is_active=data.get("is_active", True)
        )
        
        return jsonify({"id": webhook.id, "url": webhook.url, "events": webhook.events}), 201
        
    except Exception as e:
        logger.error(f"Failed to create webhook: {e}")
        return jsonify({"error": "Failed to create webhook"}), 500

@webhooks_bp.route("/api/v1/webhooks", methods=["GET"])
@jwt_required()
def get_webhooks():
    """Get all webhooks for the organization"""
    try:
        claims = get_jwt()
        organization_id = claims.get("organization_id")
        
        webhook_service = WebhookService(db.session)
        
        webhooks = webhook_service.get_webhooks_for_organization(organization_id)
        
        response_data = [
            {
                "id": wh.id,
                "url": wh.url,
                "events": wh.events,
                "is_active": wh.is_active,
                "created_at": wh.created_at.isoformat()
            }
            for wh in webhooks
        ]
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Failed to get webhooks: {e}")
        return jsonify({"error": "Failed to retrieve webhooks"}), 500

@webhooks_bp.route("/api/v1/webhooks/<int:webhook_id>", methods=["GET"])
@jwt_required()
def get_webhook(webhook_id: int):
    """Get details of a specific webhook"""
    try:
        claims = get_jwt()
        organization_id = claims.get("organization_id")
        
        webhook_service = WebhookService(db.session)
        
        webhook = webhook_service.get_webhook(webhook_id)
        
        if not webhook or webhook.organization_id != organization_id:
            return jsonify({"error": "Webhook not found"}), 404
            
        response_data = {
            "id": webhook.id,
            "url": webhook.url,
            "events": webhook.events,
            "is_active": webhook.is_active,
            "created_at": webhook.created_at.isoformat()
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Failed to get webhook {webhook_id}: {e}")
        return jsonify({"error": "Failed to retrieve webhook"}), 500

@webhooks_bp.route("/api/v1/webhooks/<int:webhook_id>", methods=["PUT"])
@jwt_required()
def update_webhook(webhook_id: int):
    """Update a webhook subscription"""
    try:
        data = request.get_json()
        claims = get_jwt()
        organization_id = claims.get("organization_id")
        
        webhook_service = WebhookService(db.session)
        
        webhook = webhook_service.get_webhook(webhook_id)
        if not webhook or webhook.organization_id != organization_id:
            return jsonify({"error": "Webhook not found"}), 404
            
        updated_webhook = webhook_service.update_webhook(webhook_id, **data)
        
        return jsonify({"id": updated_webhook.id, "message": "Webhook updated successfully"}), 200
        
    except Exception as e:
        logger.error(f"Failed to update webhook {webhook_id}: {e}")
        return jsonify({"error": "Failed to update webhook"}), 500

@webhooks_bp.route("/api/v1/webhooks/<int:webhook_id>", methods=["DELETE"])
@jwt_required()
def delete_webhook(webhook_id: int):
    """Delete a webhook subscription"""
    try:
        claims = get_jwt()
        organization_id = claims.get("organization_id")
        
        webhook_service = WebhookService(db.session)
        
        webhook = webhook_service.get_webhook(webhook_id)
        if not webhook or webhook.organization_id != organization_id:
            return jsonify({"error": "Webhook not found"}), 404
            
        success = webhook_service.delete_webhook(webhook_id)
        
        if success:
            return jsonify({"message": "Webhook deleted successfully"}), 200
        else:
            return jsonify({"error": "Failed to delete webhook"}), 500
            
    except Exception as e:
        logger.error(f"Failed to delete webhook {webhook_id}: {e}")
        return jsonify({"error": "Failed to delete webhook"}), 500

@webhooks_bp.route("/api/v1/webhooks/events", methods=["GET"])
@jwt_required()
def get_webhook_events():
    """Get webhook event history"""
    try:
        claims = get_jwt()
        organization_id = claims.get("organization_id")
        
        # In a real implementation, this would query the database for events
        # For now, return mock data
        mock_events = [
            {
                "id": 1,
                "webhook_id": 1,
                "event_type": "agent.created",
                "status": "success",
                "created_at": "2024-01-01T12:00:00Z"
            },
            {
                "id": 2,
                "webhook_id": 1,
                "event_type": "coordination.completed",
                "status": "failed",
                "created_at": "2024-01-01T12:05:00Z"
            }
        ]
        
        return jsonify(mock_events), 200
        
    except Exception as e:
        logger.error(f"Failed to get webhook events: {e}")
        return jsonify({"error": "Failed to retrieve webhook events"}), 500

@webhooks_bp.route("/api/v1/webhooks/events/<int:event_id>/retry", methods=["POST"])
@jwt_required()
def retry_webhook_event(event_id: int):
    """Manually retry a failed webhook event"""
    try:
        claims = get_jwt()
        organization_id = claims.get("organization_id")
        
        webhook_service = WebhookService(db.session)
        
        # Verify event belongs to organization before retrying
        event = db.session.query(WebhookEvent).filter_by(id=event_id).first()
        if not event or event.webhook.organization_id != organization_id:
            return jsonify({"error": "Webhook event not found"}), 404
            
        success = webhook_service.send_webhook_event(event_id)
        
        if success:
            return jsonify({"message": f"Webhook event {event_id} retry initiated"}), 202
        else:
            return jsonify({"error": f"Failed to retry webhook event {event_id}"}), 500
            
    except Exception as e:
        logger.error(f"Failed to retry webhook event {event_id}: {e}")
        return jsonify({"error": "Failed to retry webhook event"}), 500

@webhooks_bp.route("/api/v1/webhooks/test", methods=["POST"])
@jwt_required()
def test_webhook():
    """Send a test event to a webhook"""
    try:
        data = request.get_json()
        claims = get_jwt()
        organization_id = claims.get("organization_id")
        
        if not data or "webhook_id" not in data:
            return jsonify({"error": "Missing required field: webhook_id"}), 400
            
        webhook_id = data["webhook_id"]
        
        webhook_service = WebhookService(db.session)
        
        webhook = webhook_service.get_webhook(webhook_id)
        if not webhook or webhook.organization_id != organization_id:
            return jsonify({"error": "Webhook not found"}), 404
            
        # Trigger a test event
        test_payload = {"message": "This is a test event from the Brikk platform."}
        webhook_service.trigger_event("test.event", test_payload, organization_id)
        
        return jsonify({"message": f"Test event sent to webhook {webhook_id}"}), 202
        
    except Exception as e:
        logger.error(f"Failed to send test webhook event: {e}")
        return jsonify({"error": "Failed to send test event"}), 500

