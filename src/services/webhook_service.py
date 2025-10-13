"""
Webhook Service

Provides functionality for sending and receiving webhook events to enable external system integrations.
"""

import os
import json
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

import requests
from sqlalchemy.orm import Session

from src.database import db
from src.models.webhook import Webhook, WebhookEvent
from src.services.structured_logging import get_logger

logger = get_logger('brikk.webhooks')

class WebhookEventStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

@dataclass
class WebhookPayload:
    """Represents the payload for a webhook event"""
    event_type: str
    timestamp: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = None

class WebhookService:
    """Service for managing and processing webhooks"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.max_retries = int(os.getenv('WEBHOOK_MAX_RETRIES', '5'))
        self.retry_delay_seconds = int(os.getenv('WEBHOOK_RETRY_DELAY', '60'))
        
    def create_webhook(self, organization_id: int, url: str, secret: str, 
                       events: List[str], is_active: bool = True) -> Webhook:
        """Create a new webhook subscription"""
        try:
            webhook = Webhook(
                organization_id=organization_id,
                url=url,
                secret=secret,
                events=events,
                is_active=is_active
            )
            self.db.add(webhook)
            self.db.commit()
            logger.info(f"Created webhook {webhook.id} for organization {organization_id}")
            return webhook
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create webhook: {e}")
            raise
            
    def get_webhook(self, webhook_id: int) -> Optional[Webhook]:
        """Get a webhook by its ID"""
        return self.db.query(Webhook).filter_by(id=webhook_id).first()
        
    def get_webhooks_for_organization(self, organization_id: int) -> List[Webhook]:
        """Get all webhooks for an organization"""
        return self.db.query(Webhook).filter_by(organization_id=organization_id).all()
        
    def update_webhook(self, webhook_id: int, **kwargs) -> Optional[Webhook]:
        """Update a webhook's properties"""
        try:
            webhook = self.get_webhook(webhook_id)
            if not webhook:
                return None
            
            for key, value in kwargs.items():
                if hasattr(webhook, key):
                    setattr(webhook, key, value)
            
            self.db.commit()
            logger.info(f"Updated webhook {webhook_id}")
            return webhook
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update webhook {webhook_id}: {e}")
            raise
            
    def delete_webhook(self, webhook_id: int) -> bool:
        """Delete a webhook"""
        try:
            webhook = self.get_webhook(webhook_id)
            if not webhook:
                return False
            
            self.db.delete(webhook)
            self.db.commit()
            logger.info(f"Deleted webhook {webhook_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete webhook {webhook_id}: {e}")
            return False
            
    def trigger_event(self, event_type: str, payload_data: Dict[str, Any], 
                      organization_id: int, metadata: Dict[str, Any] = None) -> None:
        """Trigger a webhook event for all subscribed webhooks"""
        try:
            # Find all active webhooks subscribed to this event type
            subscribed_webhooks = self.db.query(Webhook).filter(
                Webhook.organization_id == organization_id,
                Webhook.is_active == True,
                Webhook.events.contains(event_type)
            ).all()
            
            if not subscribed_webhooks:
                logger.debug(f"No active webhooks for event {event_type} in org {organization_id}")
                return
            
            # Create payload
            payload = WebhookPayload(
                event_type=event_type,
                timestamp=datetime.now(timezone.utc).isoformat(),
                data=payload_data,
                metadata=metadata
            )
            
            # Create and send webhook events
            for webhook in subscribed_webhooks:
                self._create_and_send_webhook_event(webhook, payload)
                
        except Exception as e:
            logger.error(f"Failed to trigger event {event_type}: {e}")
            
    def _create_and_send_webhook_event(self, webhook: Webhook, payload: WebhookPayload) -> None:
        """Create a webhook event record and attempt to send it"""
        try:
            # Create event record
            event = WebhookEvent(
                webhook_id=webhook.id,
                event_type=payload.event_type,
                payload=asdict(payload),
                status=WebhookEventStatus.PENDING.value
            )
            self.db.add(event)
            self.db.commit()
            
            # Send the event
            self.send_webhook_event(event.id)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create webhook event for webhook {webhook.id}: {e}")
            
    def send_webhook_event(self, event_id: int) -> bool:
        """Send a specific webhook event"""
        try:
            event = self.db.query(WebhookEvent).filter_by(id=event_id).first()
            if not event:
                logger.warning(f"Webhook event {event_id} not found")
                return False
            
            webhook = event.webhook
            if not webhook or not webhook.is_active:
                logger.warning(f"Webhook {webhook.id} is inactive or deleted, skipping event {event_id}")
                event.status = WebhookEventStatus.FAILED.value
                self.db.commit()
                return False
            
            # Prepare payload and headers
            payload_json = json.dumps(event.payload, sort_keys=True)
            signature = self._generate_signature(webhook.secret, payload_json)
            
            headers = {
                'Content-Type': 'application/json',
                'X-Brikk-Signature': signature,
                'X-Brikk-Event-Id': str(event.id)
            }
            
            # Send request
            response = requests.post(webhook.url, data=payload_json, headers=headers, timeout=15)
            
            # Update event status
            if 200 <= response.status_code < 300:
                event.status = WebhookEventStatus.SUCCESS.value
                event.response_status_code = response.status_code
                event.response_body = response.text
                self.db.commit()
                logger.info(f"Webhook event {event_id} sent successfully to {webhook.url}")
                return True
            else:
                self._handle_failed_delivery(event, response)
                return False
                
        except Exception as e:
            logger.error(f"Failed to send webhook event {event_id}: {e}")
            event.status = WebhookEventStatus.FAILED.value
            self.db.commit()
            return False
            
    def retry_failed_events(self) -> None:
        """Retry sending failed webhook events"""
        try:
            failed_events = self.db.query(WebhookEvent).filter(
                WebhookEvent.status == WebhookEventStatus.FAILED.value,
                WebhookEvent.retry_count < self.max_retries
            ).all()
            
            for event in failed_events:
                logger.info(f"Retrying webhook event {event.id} (attempt {event.retry_count + 1})")
                self.send_webhook_event(event.id)
                
        except Exception as e:
            logger.error(f"Failed to retry failed webhook events: {e}")
            
    def _handle_failed_delivery(self, event: WebhookEvent, response: requests.Response) -> None:
        """Handle a failed webhook delivery attempt"""
        try:
            event.status = WebhookEventStatus.FAILED.value
            event.response_status_code = response.status_code
            event.response_body = response.text
            event.retry_count += 1
            self.db.commit()
            
            logger.warning(f"Webhook event {event.id} failed to deliver to {event.webhook.url} with status {response.status_code}")
            
            # Schedule retry if applicable
            if event.retry_count < self.max_retries:
                # In a real implementation, this would use a background job queue (e.g., Celery)
                logger.info(f"Scheduling retry for webhook event {event.id}")
            else:
                logger.error(f"Webhook event {event.id} has reached max retries and will not be sent again")
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to handle failed delivery for event {event.id}: {e}")
            
    def _generate_signature(self, secret: str, payload: str) -> str:
        """Generate HMAC-SHA256 signature for webhook payload"""
        return hmac.new(secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()

    def verify_signature(self, secret: str, payload: str, received_signature: str) -> bool:
        """Verify the signature of an incoming webhook"""
        if not received_signature:
            return False
            
        expected_signature = self._generate_signature(secret, payload)
        return hmac.compare_digest(expected_signature, received_signature)

