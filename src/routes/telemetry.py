# -*- coding: utf-8 -*-
"""
Telemetry Routes for SDK Event Collection.

Allows SDKs and client applications to send telemetry events for monitoring and debugging.
"""
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime

telemetry_bp = Blueprint('telemetry', __name__)


@telemetry_bp.route('/events', methods=['POST'])
def collect_events():
    """
    Collect telemetry events from SDKs.
    
    Request:
        {
            "events": [
                {
                    "event_type": "api_call",
                    "timestamp": "2025-10-15T19:30:00Z",
                    "sdk_version": "1.0.0",
                    "sdk_language": "python",
                    "endpoint": "/api/v1/agents",
                    "method": "GET",
                    "status_code": 200,
                    "duration_ms": 150,
                    "error": null,
                    "metadata": {
                        "custom_field": "value"
                    }
                }
            ],
            "sdk_info": {
                "name": "brikk-python-sdk",
                "version": "1.0.0",
                "language": "python",
                "platform": "linux"
            }
        }
    
    Response (202 Accepted):
        {
            "message": "Events received",
            "events_count": 1
        }
    """
    data = request.get_json(silent=True) or {}
    
    events = data.get('events', [])
    sdk_info = data.get('sdk_info', {})
    
    if not events:
        return jsonify({
            'error': 'validation_error',
            'message': 'No events provided'
        }), 400
    
    # Log events for monitoring
    current_app.logger.info(
        f"Telemetry events received: {len(events)} events from "
        f"{sdk_info.get('name', 'unknown')} v{sdk_info.get('version', 'unknown')}"
    )
    
    # Process each event
    for event in events:
        event_type = event.get('event_type')
        
        # Log to application logs
        current_app.logger.debug(
            f"Telemetry event: {event_type}",
            extra={
                'event': event,
                'sdk_info': sdk_info
            }
        )
        
        # TODO: Store in database or send to analytics platform
        # For now, just log to stdout/stderr
    
    return jsonify({
        'message': 'Events received',
        'events_count': len(events)
    }), 202


@telemetry_bp.route('/health', methods=['GET'])
def telemetry_health():
    """
    Health check for telemetry endpoint.
    
    Response (200 OK):
        {
            "status": "healthy",
            "timestamp": "2025-10-15T19:30:00Z"
        }
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200

