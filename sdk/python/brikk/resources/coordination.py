# -*- coding: utf-8 -*-
"""Coordination and messaging resources."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from .._http import HTTPClient

from ..types import CoordinationMessage


class CoordinationResource:
    """Coordination and inter-agent messaging operations."""

    def __init__(self, http_client: "HTTPClient"):
        self._http = http_client

    def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        payload: Dict[str, Any],
        message_type: str = "event",
        ttl_ms: int = 60000,
    ) -> Dict[str, Any]:
        """Send a coordination message between agents.

        Args:
            sender_id: Sender agent ID
            recipient_id: Recipient agent ID
            payload: Message payload dict
            message_type: Message type (default: "event")
            ttl_ms: Time-to-live in milliseconds (default: 60000)

        Returns:
            Delivery receipt

        Example:
            >>> receipt = client.coordination.send_message(
            ...     sender_id="agent_1",
            ...     recipient_id="agent_2",
            ...     payload={"action": "process", "data": {...}}
            ... )
        """
        message: CoordinationMessage = {
            "version": "1.0",
            "message_id": str(uuid.uuid4()),
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "type": message_type,
            "sender": {"agent_id": sender_id},
            "recipient": {"agent_id": recipient_id},
            "payload": payload,
            "ttl_ms": ttl_ms,
        }
        return self._http.post("/api/v1/coordination", json_data=message, use_hmac=True)

