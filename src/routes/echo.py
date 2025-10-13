# src/routes/echo.py
"""
Stage 1 Echo Workflow - Simple message echo for testing agent communication.

POST /api/v1/echo
- Accepts a message payload
- Logs the message
- Returns the same message with metadata
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from flask import Blueprint, request, jsonify, g, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from src.database import db
from src.models.message_log import MessageLog
from src.services.audit import log_echo_sent

# Rate limiting setup
def rate_key() -> str:
    """Use user ID if available, otherwise IP address"""
    try:
        user_id = getattr(g.user, 'id', None) if hasattr(g, 'user') and g.user else None
        return f"user:{user_id}" if user_id else get_remote_address()
    except:
        return get_remote_address()

limiter = Limiter(
    key_func=rate_key,
    default_limits=["100 per minute", "1000 per hour"]
)

echo_bp = Blueprint("echo_bp", __name__, url_prefix="/api/v1/echo")


@echo_bp.route("", methods=["POST"])
@echo_bp.route("/", methods=["POST"])
@limiter.limit("50 per minute")
def send_echo():
    """
    Echo workflow - accepts a message and returns it with metadata.
    
    Expected payload:
    {
        "message": "Hello, world!",
        "sender_id": "agent-uuid-optional"
    }
    
    Returns:
    {
        "id": "message-uuid",
        "message": "Hello, world!",
        "echo": "Hello, world!",
        "timestamp": "2024-01-01T12:00:00Z",
        "status": "success"
    }
    """
    # Basic auth check
    if not hasattr(g, 'user') or not g.user:
        return jsonify({"error": "unauthorized", "message": "Authentication required"}), 401
    
    user_id = getattr(g.user, 'id', None)
    if not user_id:
        return jsonify({"error": "unauthorized", "message": "User ID not found"}), 401

    payload = request.get_json(silent=True) or {}
    
    # Validate message
    message = payload.get('message', '').strip()
    if not message:
        return jsonify({"error": "validation_error", "message": "Message is required"}), 400
    
    if len(message) > 10000:  # 10KB limit
        return jsonify({"error": "validation_error", "message": "Message too long (max 10KB)"}), 400
    
    sender_id = payload.get('sender_id')  # Optional agent ID
    
    try:
        # Create message log entry
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        
        # Build request payload for logging
        request_payload = {
            "message": message,
            "sender_id": sender_id,
            "timestamp": timestamp.isoformat()
        }
        
        # Build response payload
        response_payload = {
            "id": message_id,
            "message": message,
            "echo": message,  # Simple echo - return the same message
            "timestamp": timestamp.isoformat(),
            "status": "success"
        }
        
        # Log the message
        message_log = MessageLog(
            id=message_id,
            owner_id=user_id,
            sender_id=sender_id,
            request_payload=request_payload,
            response_payload=response_payload,
            status="success"
        )
        
        db.session.add(message_log)
        db.session.commit()
        
        # Audit log
        try:
            log_echo_sent(user_id, message_id, sender_id or "unknown")
        except Exception as e:
            current_app.logger.warning(f"Failed to create audit log: {e}")
        
        return jsonify(response_payload), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Echo workflow failed: {e}")
        return jsonify({"error": "internal_error", "message": "Echo workflow failed"}), 500


@echo_bp.route("/logs", methods=["GET"])
@limiter.limit("100 per minute")
def get_echo_logs():
    """
    Get echo message logs for the authenticated user.
    
    Query parameters:
    - limit: Number of logs to return (default 50, max 200)
    - offset: Number of logs to skip (default 0)
    
    Returns:
    {
        "logs": [
            {
                "id": "message-uuid",
                "request_payload": {...},
                "response_payload": {...},
                "status": "success",
                "created_at": "2024-01-01T12:00:00Z"
            }
        ],
        "total": 123
    }
    """
    # Basic auth check
    if not hasattr(g, 'user') or not g.user:
        return jsonify({"error": "unauthorized", "message": "Authentication required"}), 401
    
    user_id = getattr(g.user, 'id', None)
    if not user_id:
        return jsonify({"error": "unauthorized", "message": "User ID not found"}), 401

    # Parse query parameters
    try:
        limit = min(int(request.args.get('limit', 50)), 200)
        offset = max(int(request.args.get('offset', 0)), 0)
    except ValueError:
        return jsonify({"error": "validation_error", "message": "Invalid limit or offset"}), 400

    try:
        # Query message logs for this user
        query = db.session.query(MessageLog).filter(MessageLog.owner_id == user_id)
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        logs = query.order_by(MessageLog.created_at.desc()).offset(offset).limit(limit).all()
        
        # Format response
        log_data = []
        for log in logs:
            log_data.append({
                "id": log.id,
                "sender_id": log.sender_id,
                "request_payload": log.request_payload,
                "response_payload": log.response_payload,
                "status": log.status,
                "created_at": log.created_at.isoformat() if log.created_at else None
            })
        
        return jsonify({
            "logs": log_data,
            "total": total,
            "limit": limit,
            "offset": offset
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to get echo logs: {e}")
        return jsonify({"error": "internal_error", "message": "Failed to get logs"}), 500
