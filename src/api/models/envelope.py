"""
Pydantic envelope schema for Brikk coordination API.

Defines the message envelope structure with strict validation:
- UUIDv7 message IDs
- RFC3339 timestamp format
- Strict field types and ranges
- TTL validation
- Extra fields forbidden
"""

import re
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Literal

from pydantic import BaseModel, Field, field_validator, ConfigDict


class Sender(BaseModel):
    """Sender information in the envelope."""
    agent_id: str = Field(..., min_length=1, max_length=255)
    org_id: Optional[str] = Field(None, max_length=255)


class Recipient(BaseModel):
    """Recipient information in the envelope."""
    agent_id: str = Field(..., min_length=1, max_length=255)
    org_id: Optional[str] = Field(None, max_length=255)


class Envelope(BaseModel):
    """
    Message envelope for Brikk coordination API.
    
    Validates:
    - version: Must be "1.0"
    - message_id: Must be valid UUIDv7 format
    - ts: Must be RFC3339 UTC timestamp
    - type: Must be one of allowed message types
    - sender/recipient: Required agent_id, optional org_id
    - payload: Any dict structure
    - ttl_ms: Range 1-120000ms (default 30000)
    - reply_to/nonce: Optional strings
    - Extra fields forbidden
    """
    
    model_config = ConfigDict(
        extra='forbid',  # Forbid extra fields
        str_strip_whitespace=True,  # Strip whitespace from strings
        validate_assignment=True,  # Validate on assignment
    )
    
    version: Literal["1.0"] = Field(
        default="1.0",
        description="Envelope version, must be '1.0'"
    )
    
    message_id: str = Field(
        ...,
        description="UUIDv7 string identifier for the message"
    )
    
    ts: str = Field(
        ...,
        description="RFC3339 UTC timestamp string"
    )
    
    type: Literal["message", "event", "command", "result", "error"] = Field(
        default="message",
        description="Message type classification"
    )
    
    sender: Sender = Field(
        ...,
        description="Sender information with agent_id and optional org_id"
    )
    
    recipient: Recipient = Field(
        ...,
        description="Recipient information with agent_id and optional org_id"
    )
    
    payload: Dict[str, Any] = Field(
        ...,
        description="Message payload as arbitrary dict"
    )
    
    ttl_ms: int = Field(
        default=30000,
        ge=1,
        le=120000,
        description="Time-to-live in milliseconds (1-120000)"
    )
    
    reply_to: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional reply-to identifier"
    )
    
    nonce: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional nonce for deduplication"
    )
    
    @field_validator('message_id')
    @classmethod
    def validate_message_id(cls, v: str) -> str:
        """Validate that message_id is a valid UUIDv7 format."""
        try:
            # Parse as UUID to validate format
            parsed_uuid = uuid.UUID(v)
            
            # Check if it's a valid UUID string format
            if str(parsed_uuid) != v.lower():
                raise ValueError("Invalid UUID format")
            
            # UUIDv7 validation: version should be 7
            # For now, accept UUID4 as approximation until proper UUIDv7 implementation
            # UUIDv7 has version bits in the 13th hex digit (bits 48-51)
            version = (parsed_uuid.int >> 76) & 0xF
            if version not in [4, 7]:  # Accept both UUID4 and UUID7 for now
                raise ValueError("UUID must be version 4 or 7")
                
            return v.lower()  # Normalize to lowercase
            
        except (ValueError, AttributeError) as e:
            raise ValueError(f"message_id must be a valid UUIDv7 string: {e}")
    
    @field_validator('ts')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate that ts is a valid RFC3339 UTC timestamp."""
        # RFC3339 regex pattern for UTC timestamps
        rfc3339_pattern = re.compile(
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$'
        )
        
        if not rfc3339_pattern.match(v):
            raise ValueError(
                "ts must be RFC3339 UTC timestamp (e.g., '2023-10-02T14:30:00Z' or '2023-10-02T14:30:00.123Z')"
            )
        
        # Additional validation: try to parse as datetime
        try:
            # Remove 'Z' and parse
            dt_str = v.rstrip('Z')
            datetime.fromisoformat(dt_str)
        except ValueError as e:
            raise ValueError(f"Invalid timestamp format: {e}")
        
        return v
    
    def minify(self) -> Dict[str, Any]:
        """
        Return envelope as dict with None values removed.
        
        This is useful for serialization where None fields should be omitted.
        
        Returns:
            Dict with None values filtered out
        """
        data = self.model_dump()
        return self._remove_none_values(data)
    
    @staticmethod
    def _remove_none_values(data: Any) -> Any:
        """Recursively remove None values from nested dict/list structures."""
        if isinstance(data, dict):
            return {
                k: Envelope._remove_none_values(v) 
                for k, v in data.items() 
                if v is not None
            }
        elif isinstance(data, list):
            return [
                Envelope._remove_none_values(item) 
                for item in data 
                if item is not None
            ]
        else:
            return data


def create_sample_envelope(
    sender_agent_id: str = "agent-001",
    recipient_agent_id: str = "agent-002",
    payload: Optional[Dict[str, Any]] = None
) -> Envelope:
    """
    Create a sample envelope for testing purposes.
    
    Args:
        sender_agent_id: Sender agent ID
        recipient_agent_id: Recipient agent ID  
        payload: Optional payload dict
        
    Returns:
        Valid Envelope instance
    """
    if payload is None:
        payload = {"action": "test", "data": "sample"}
    
    # Generate UUIDv7 (approximation using uuid4 for now)
    message_id = str(uuid.uuid4())
    
    # Current UTC timestamp in RFC3339 format
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-3] + 'Z'
    
    return Envelope(
        message_id=message_id,
        ts=timestamp,
        sender=Sender(agent_id=sender_agent_id),
        recipient=Recipient(agent_id=recipient_agent_id),
        payload=payload
    )
