"""
Alerting Service

Provides automated alerting, notifications, and escalation capabilities.
Supports multiple notification channels and intelligent alert routing.
"""

import os
import json
import smtplib
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.services.structured_logging import get_logger
from src.services.monitoring_service import Alert, AlertSeverity

logger = get_logger('brikk.alerting')

class NotificationChannel(Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"
    PAGERDUTY = "pagerduty"

@dataclass
class NotificationRule:
    """Defines when and how to send notifications"""
    id: str
    name: str
    channels: List[NotificationChannel]
    severity_threshold: AlertSeverity
    recipients: List[str]
    escalation_delay_minutes: int = 15
    max_escalations: int = 3
    enabled: bool = True

@dataclass
class NotificationTemplate:
    """Template for notification messages"""
    channel: NotificationChannel
    subject_template: str
    body_template: str
    format_type: str = "text"  # text, html, markdown

class AlertingService:
    """Comprehensive alerting and notification service"""
    
    def __init__(self):
        self.notification_rules = self._load_notification_rules()
        self.templates = self._load_notification_templates()
        self.sent_notifications = {}  # Track sent notifications to prevent spam
        
    def _load_notification_rules(self) -> List[NotificationRule]:
        """Load notification rules from configuration"""
        return [
            NotificationRule(
                id="critical_alerts",
                name="Critical Alert Notifications",
                channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
                severity_threshold=AlertSeverity.CRITICAL,
                recipients=["admin@brikk.com", "ops@brikk.com"],
                escalation_delay_minutes=5,
                max_escalations=5
            ),
            NotificationRule(
                id="high_alerts",
                name="High Priority Alert Notifications",
                channels=[NotificationChannel.EMAIL],
                severity_threshold=AlertSeverity.HIGH,
                recipients=["ops@brikk.com"],
                escalation_delay_minutes=15,
                max_escalations=3
            ),
            NotificationRule(
                id="medium_alerts",
                name="Medium Priority Alert Notifications",
                channels=[NotificationChannel.SLACK],
                severity_threshold=AlertSeverity.MEDIUM,
                recipients=["#alerts"],
                escalation_delay_minutes=30,
                max_escalations=2
            )
        ]
    
    def _load_notification_templates(self) -> Dict[NotificationChannel, NotificationTemplate]:
        """Load notification templates for different channels"""
        return {
            NotificationChannel.EMAIL: NotificationTemplate(
                channel=NotificationChannel.EMAIL,
                subject_template="[Brikk Alert] {severity}: {alert_name}",
                body_template="""
Alert: {alert_name}
Severity: {severity}
Description: {description}
Triggered At: {triggered_at}
System: Brikk Agent Coordination Platform

Details:
{details}

Please investigate immediately.

---
Brikk Monitoring System
                """.strip(),
                format_type="text"
            ),
            NotificationChannel.SLACK: NotificationTemplate(
                channel=NotificationChannel.SLACK,
                subject_template="",
                body_template="""
🚨 *{severity.upper()} ALERT*

*{alert_name}*
{description}

*Triggered:* {triggered_at}
*System:* Brikk Platform

{details}
                """.strip(),
                format_type="markdown"
            ),
            NotificationChannel.WEBHOOK: NotificationTemplate(
                channel=NotificationChannel.WEBHOOK,
                subject_template="",
                body_template=json.dumps({
                    "alert_name": "{alert_name}",
                    "severity": "{severity}",
                    "description": "{description}",
                    "triggered_at": "{triggered_at}",
                    "details": "{details}"
                }),
                format_type="json"
            )
        }
    
    def process_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Process an alert and send appropriate notifications"""
        try:
            alert_id = alert_data.get('id')
            severity = AlertSeverity(alert_data.get('severity', 'low'))
            
            # Check if we've already sent notifications for this alert recently
            if self._is_notification_suppressed(alert_id):
                logger.debug(f"Notification suppressed for alert {alert_id}")
                return True
            
            # Find applicable notification rules
            applicable_rules = [
                rule for rule in self.notification_rules
                if rule.enabled and self._severity_meets_threshold(severity, rule.severity_threshold)
            ]
            
            if not applicable_rules:
                logger.debug(f"No applicable notification rules for alert {alert_id}")
                return True
            
            # Send notifications for each applicable rule
            success = True
            for rule in applicable_rules:
                rule_success = self._send_notifications_for_rule(alert_data, rule)
                success = success and rule_success
            
            # Track that we've sent notifications for this alert
            self._record_notification_sent(alert_id)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to process alert {alert_data.get('id', 'unknown')}: {e}")
            return False
    
    def send_test_notification(self, channel: NotificationChannel, recipient: str) -> bool:
        """Send a test notification to verify channel configuration"""
        try:
            test_alert = {
                'id': 'test_alert',
                'name': 'Test Notification',
                'severity': 'low',
                'description': 'This is a test notification to verify alerting configuration.',
                'triggered_at': datetime.now(timezone.utc).isoformat(),
                'details': 'All systems operational. This is only a test.'
            }
            
            if channel == NotificationChannel.EMAIL:
                return self._send_email_notification(test_alert, [recipient])
            elif channel == NotificationChannel.SLACK:
                return self._send_slack_notification(test_alert, [recipient])
            elif channel == NotificationChannel.WEBHOOK:
                return self._send_webhook_notification(test_alert, [recipient])
            else:
                logger.warning(f"Test notification not implemented for channel: {channel}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send test notification: {e}")
            return False
    
    def get_notification_status(self) -> Dict[str, Any]:
        """Get status of notification channels and recent activity"""
        try:
            status = {
                'channels': {},
                'recent_notifications': len(self.sent_notifications),
                'notification_rules': len([r for r in self.notification_rules if r.enabled]),
                'last_check': datetime.now(timezone.utc).isoformat()
            }
            
            # Check each channel's configuration
            for channel in NotificationChannel:
                status['channels'][channel.value] = self._check_channel_configuration(channel)
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get notification status: {e}")
            return {'error': str(e)}
    
    def _send_notifications_for_rule(self, alert_data: Dict[str, Any], rule: NotificationRule) -> bool:
        """Send notifications for a specific rule"""
        success = True
        
        for channel in rule.channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    channel_success = self._send_email_notification(alert_data, rule.recipients)
                elif channel == NotificationChannel.SLACK:
                    channel_success = self._send_slack_notification(alert_data, rule.recipients)
                elif channel == NotificationChannel.WEBHOOK:
                    channel_success = self._send_webhook_notification(alert_data, rule.recipients)
                else:
                    logger.warning(f"Notification channel not implemented: {channel}")
                    channel_success = False
                
                success = success and channel_success
                
            except Exception as e:
                logger.error(f"Failed to send notification via {channel}: {e}")
                success = False
        
        return success
    
    def _send_email_notification(self, alert_data: Dict[str, Any], recipients: List[str]) -> bool:
        """Send email notification"""
        try:
            # Get email configuration
            smtp_server = os.getenv('SMTP_SERVER', 'localhost')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_username = os.getenv('SMTP_USERNAME')
            smtp_password = os.getenv('SMTP_PASSWORD')
            from_email = os.getenv('FROM_EMAIL', 'alerts@brikk.com')
            
            if not smtp_username or not smtp_password:
                logger.warning("SMTP credentials not configured, skipping email notification")
                return False
            
            # Format message using template
            template = self.templates[NotificationChannel.EMAIL]
            subject = template.subject_template.format(**alert_data)
            body = template.body_template.format(**alert_data)
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent for alert {alert_data.get('id')} to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _send_slack_notification(self, alert_data: Dict[str, Any], recipients: List[str]) -> bool:
        """Send Slack notification"""
        try:
            webhook_url = os.getenv('SLACK_WEBHOOK_URL')
            if not webhook_url:
                logger.warning("Slack webhook URL not configured, skipping Slack notification")
                return False
            
            # Format message using template
            template = self.templates[NotificationChannel.SLACK]
            message = template.body_template.format(**alert_data)
            
            # Determine color based on severity
            severity = alert_data.get('severity', 'low')
            color_map = {
                'critical': '#FF0000',
                'high': '#FF8C00',
                'medium': '#FFD700',
                'low': '#32CD32'
            }
            
            # Create Slack payload
            payload = {
                'text': f"Alert: {alert_data.get('name', 'Unknown')}",
                'attachments': [{
                    'color': color_map.get(severity, '#808080'),
                    'text': message,
                    'ts': int(datetime.now().timestamp())
                }]
            }
            
            # Send to Slack
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Slack notification sent for alert {alert_data.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    def _send_webhook_notification(self, alert_data: Dict[str, Any], webhook_urls: List[str]) -> bool:
        """Send webhook notification"""
        try:
            # Format payload using template
            template = self.templates[NotificationChannel.WEBHOOK]
            payload_str = template.body_template.format(**alert_data)
            payload = json.loads(payload_str)
            
            success = True
            for webhook_url in webhook_urls:
                try:
                    response = requests.post(webhook_url, json=payload, timeout=10)
                    response.raise_for_status()
                    logger.info(f"Webhook notification sent to {webhook_url}")
                except Exception as e:
                    logger.error(f"Failed to send webhook to {webhook_url}: {e}")
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False
    
    def _is_notification_suppressed(self, alert_id: str) -> bool:
        """Check if notifications should be suppressed for this alert"""
        if alert_id not in self.sent_notifications:
            return False
        
        last_sent = self.sent_notifications[alert_id]
        suppression_window = timedelta(minutes=15)  # Don't send same alert more than once per 15 minutes
        
        return datetime.now(timezone.utc) - last_sent < suppression_window
    
    def _record_notification_sent(self, alert_id: str) -> None:
        """Record that a notification was sent for an alert"""
        self.sent_notifications[alert_id] = datetime.now(timezone.utc)
        
        # Clean up old entries (keep only last 24 hours)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        self.sent_notifications = {
            k: v for k, v in self.sent_notifications.items() 
            if v > cutoff
        }
    
    def _severity_meets_threshold(self, alert_severity: AlertSeverity, threshold: AlertSeverity) -> bool:
        """Check if alert severity meets the notification threshold"""
        severity_levels = {
            AlertSeverity.LOW: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.HIGH: 3,
            AlertSeverity.CRITICAL: 4
        }
        
        return severity_levels[alert_severity] >= severity_levels[threshold]
    
    def _check_channel_configuration(self, channel: NotificationChannel) -> Dict[str, Any]:
        """Check if a notification channel is properly configured"""
        try:
            if channel == NotificationChannel.EMAIL:
                smtp_configured = bool(os.getenv('SMTP_USERNAME') and os.getenv('SMTP_PASSWORD'))
                return {
                    'configured': smtp_configured,
                    'status': 'ready' if smtp_configured else 'missing_credentials'
                }
            
            elif channel == NotificationChannel.SLACK:
                webhook_configured = bool(os.getenv('SLACK_WEBHOOK_URL'))
                return {
                    'configured': webhook_configured,
                    'status': 'ready' if webhook_configured else 'missing_webhook_url'
                }
            
            elif channel == NotificationChannel.WEBHOOK:
                return {
                    'configured': True,
                    'status': 'ready'
                }
            
            else:
                return {
                    'configured': False,
                    'status': 'not_implemented'
                }
                
        except Exception as e:
            return {
                'configured': False,
                'status': 'error',
                'error': str(e)
            }

# Global alerting service instance
alerting_service = AlertingService()
