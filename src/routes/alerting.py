"""
Alerting Routes

Provides API endpoints for managing alerts, notifications, and alerting configuration.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from src.services.alerting_service import alerting_service, NotificationChannel
from src.services.monitoring_service import monitoring_service
from src.services.structured_logging import get_logger

logger = get_logger('brikk.alerting.routes')

alerting_bp = Blueprint("alerting", __name__)

@alerting_bp.route("/api/v1/alerting/status", methods=["GET"])
@jwt_required()
def get_alerting_status():
    """
    Get the status of the alerting system and notification channels
    """
    try:
        status = alerting_service.get_notification_status()
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Failed to get alerting status: {e}")
        return jsonify({'error': 'Failed to retrieve alerting status'}), 500

@alerting_bp.route("/api/v1/alerting/test", methods=["POST"])
@jwt_required()
def send_test_alert():
    """
    Send a test notification to verify alerting configuration
    
    Request body:
    {
        "channel": "email|slack|webhook",
        "recipient": "email@example.com or webhook URL"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'channel' not in data or 'recipient' not in data:
            return jsonify({'error': 'Missing required fields: channel, recipient'}), 400
        
        channel_str = data['channel'].lower()
        recipient = data['recipient']
        
        # Validate channel
        try:
            channel = NotificationChannel(channel_str)
        except ValueError:
            return jsonify({'error': f'Invalid channel: {channel_str}'}), 400
        
        # Send test notification
        success = alerting_service.send_test_notification(channel, recipient)
        
        if success:
            return jsonify({
                'message': f'Test notification sent successfully to {recipient} via {channel_str}',
                'success': True
            }), 200
        else:
            return jsonify({
                'message': f'Failed to send test notification to {recipient} via {channel_str}',
                'success': False
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to send test alert: {e}")
        return jsonify({'error': 'Failed to send test alert'}), 500

@alerting_bp.route("/api/v1/alerting/alerts/active", methods=["GET"])
@jwt_required()
def get_active_alerts():
    """
    Get all currently active alerts
    """
    try:
        active_alerts = monitoring_service.check_alerts()
        
        # Enrich alerts with additional information
        enriched_alerts = []
        for alert in active_alerts:
            enriched_alert = alert.copy()
            enriched_alert['duration_minutes'] = 0  # Would calculate actual duration
            enriched_alert['escalation_level'] = 1  # Would track escalation level
            enriched_alerts.append(enriched_alert)
        
        response_data = {
            'alerts': enriched_alerts,
            'total_count': len(enriched_alerts),
            'critical_count': len([a for a in enriched_alerts if a.get('severity') == 'critical']),
            'high_count': len([a for a in enriched_alerts if a.get('severity') == 'high']),
            'medium_count': len([a for a in enriched_alerts if a.get('severity') == 'medium']),
            'low_count': len([a for a in enriched_alerts if a.get('severity') == 'low'])
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        return jsonify({'error': 'Failed to retrieve active alerts'}), 500

@alerting_bp.route("/api/v1/alerting/alerts/<alert_id>/acknowledge", methods=["POST"])
@jwt_required()
def acknowledge_alert(alert_id: str):
    """
    Acknowledge an alert to stop further notifications
    
    Request body:
    {
        "acknowledged_by": "user_id or email",
        "note": "Optional acknowledgment note"
    }
    """
    try:
        data = request.get_json() or {}
        claims = get_jwt()
        
        acknowledged_by = data.get('acknowledged_by', claims.get('email', 'unknown'))
        note = data.get('note', '')
        
        # In a real implementation, this would update the alert status in the database
        # For now, we'll just log the acknowledgment
        logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}: {note}")
        
        response_data = {
            'alert_id': alert_id,
            'acknowledged': True,
            'acknowledged_by': acknowledged_by,
            'acknowledged_at': monitoring_service._get_current_timestamp(),
            'note': note
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
        return jsonify({'error': 'Failed to acknowledge alert'}), 500

@alerting_bp.route("/api/v1/alerting/alerts/<alert_id>/resolve", methods=["POST"])
@jwt_required()
def resolve_alert(alert_id: str):
    """
    Manually resolve an alert
    
    Request body:
    {
        "resolved_by": "user_id or email",
        "resolution_note": "Description of how the alert was resolved"
    }
    """
    try:
        data = request.get_json() or {}
        claims = get_jwt()
        
        resolved_by = data.get('resolved_by', claims.get('email', 'unknown'))
        resolution_note = data.get('resolution_note', '')
        
        # In a real implementation, this would update the alert status in the database
        logger.info(f"Alert {alert_id} resolved by {resolved_by}: {resolution_note}")
        
        response_data = {
            'alert_id': alert_id,
            'resolved': True,
            'resolved_by': resolved_by,
            'resolved_at': monitoring_service._get_current_timestamp(),
            'resolution_note': resolution_note
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Failed to resolve alert {alert_id}: {e}")
        return jsonify({'error': 'Failed to resolve alert'}), 500

@alerting_bp.route("/api/v1/alerting/notifications/history", methods=["GET"])
@jwt_required()
def get_notification_history():
    """
    Get notification history
    
    Query parameters:
    - limit: Number of notifications to return (default: 50)
    - offset: Offset for pagination (default: 0)
    - channel: Filter by notification channel (optional)
    """
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        channel_filter = request.args.get('channel')
        
        # In a real implementation, this would query the notification history from the database
        # For now, return mock data
        mock_notifications = [
            {
                'id': f'notif_{i}',
                'alert_id': f'alert_{i % 5}',
                'channel': 'email',
                'recipient': 'admin@brikk.com',
                'sent_at': '2024-01-01T12:00:00Z',
                'status': 'delivered',
                'subject': f'Alert {i}: System Issue'
            }
            for i in range(offset, offset + limit)
        ]
        
        if channel_filter:
            mock_notifications = [n for n in mock_notifications if n['channel'] == channel_filter]
        
        response_data = {
            'notifications': mock_notifications,
            'total_count': 1000,  # Mock total
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < 1000
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Failed to get notification history: {e}")
        return jsonify({'error': 'Failed to retrieve notification history'}), 500

@alerting_bp.route("/api/v1/alerting/rules", methods=["GET"])
@jwt_required()
def get_alert_rules():
    """
    Get all configured alert rules
    """
    try:
        # In a real implementation, this would return actual alert rules from the database
        mock_rules = [
            {
                'id': 'high_error_rate',
                'name': 'High Error Rate',
                'description': 'Triggers when error rate exceeds 5%',
                'condition': 'error_rate > 0.05',
                'severity': 'high',
                'enabled': True,
                'notification_channels': ['email', 'slack'],
                'created_at': '2024-01-01T00:00:00Z',
                'updated_at': '2024-01-01T00:00:00Z'
            },
            {
                'id': 'agent_down',
                'name': 'Agent Down',
                'description': 'Triggers when an agent becomes unresponsive',
                'condition': 'agent_inactive_minutes > 10',
                'severity': 'critical',
                'enabled': True,
                'notification_channels': ['email', 'slack', 'pagerduty'],
                'created_at': '2024-01-01T00:00:00Z',
                'updated_at': '2024-01-01T00:00:00Z'
            }
        ]
        
        return jsonify({'rules': mock_rules}), 200
        
    except Exception as e:
        logger.error(f"Failed to get alert rules: {e}")
        return jsonify({'error': 'Failed to retrieve alert rules'}), 500

@alerting_bp.route("/api/v1/alerting/rules", methods=["POST"])
@jwt_required()
def create_alert_rule():
    """
    Create a new alert rule
    
    Request body:
    {
        "name": "Rule name",
        "description": "Rule description",
        "condition": "metric_name > threshold",
        "severity": "low|medium|high|critical",
        "notification_channels": ["email", "slack"],
        "enabled": true
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        required_fields = ['name', 'condition', 'severity']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        # Validate severity
        valid_severities = ['low', 'medium', 'high', 'critical']
        if data['severity'] not in valid_severities:
            return jsonify({'error': f'Invalid severity. Must be one of: {", ".join(valid_severities)}'}), 400
        
        # In a real implementation, this would save the rule to the database
        rule_id = f"rule_{len(data['name'].split())}"  # Mock ID generation
        
        response_data = {
            'id': rule_id,
            'name': data['name'],
            'description': data.get('description', ''),
            'condition': data['condition'],
            'severity': data['severity'],
            'notification_channels': data.get('notification_channels', []),
            'enabled': data.get('enabled', True),
            'created_at': monitoring_service._get_current_timestamp()
        }
        
        logger.info(f"Created alert rule: {rule_id}")
        
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"Failed to create alert rule: {e}")
        return jsonify({'error': 'Failed to create alert rule'}), 500

@alerting_bp.route("/api/v1/alerting/rules/<rule_id>", methods=["PUT"])
@jwt_required()
def update_alert_rule(rule_id: str):
    """
    Update an existing alert rule
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        # In a real implementation, this would update the rule in the database
        logger.info(f"Updated alert rule: {rule_id}")
        
        response_data = {
            'id': rule_id,
            'updated_at': monitoring_service._get_current_timestamp(),
            'message': 'Alert rule updated successfully'
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Failed to update alert rule {rule_id}: {e}")
        return jsonify({'error': 'Failed to update alert rule'}), 500

@alerting_bp.route("/api/v1/alerting/rules/<rule_id>", methods=["DELETE"])
@jwt_required()
def delete_alert_rule(rule_id: str):
    """
    Delete an alert rule
    """
    try:
        # In a real implementation, this would delete the rule from the database
        logger.info(f"Deleted alert rule: {rule_id}")
        
        return jsonify({'message': 'Alert rule deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Failed to delete alert rule {rule_id}: {e}")
        return jsonify({'error': 'Failed to delete alert rule'}), 500

@alerting_bp.route("/api/v1/alerting/channels", methods=["GET"])
@jwt_required()
def get_notification_channels():
    """
    Get available notification channels and their configuration status
    """
    try:
        status = alerting_service.get_notification_status()
        channels = status.get('channels', {})
        
        # Add additional information about each channel
        channel_info = {
            'email': {
                'name': 'Email',
                'description': 'Send notifications via email',
                'configuration_required': ['SMTP_SERVER', 'SMTP_USERNAME', 'SMTP_PASSWORD'],
                'status': channels.get('email', {})
            },
            'slack': {
                'name': 'Slack',
                'description': 'Send notifications to Slack channels',
                'configuration_required': ['SLACK_WEBHOOK_URL'],
                'status': channels.get('slack', {})
            },
            'webhook': {
                'name': 'Webhook',
                'description': 'Send notifications to custom webhook endpoints',
                'configuration_required': [],
                'status': channels.get('webhook', {})
            }
        }
        
        return jsonify({'channels': channel_info}), 200
        
    except Exception as e:
        logger.error(f"Failed to get notification channels: {e}")
        return jsonify({'error': 'Failed to retrieve notification channels'}), 500
