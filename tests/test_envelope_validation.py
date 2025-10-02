"""
Test suite for envelope schema validation.

Tests:
- Valid minimal envelope → 202 with echo.message_id
- Extra/unknown fields → 422
- Bad type/uuid/timestamp → 422
- TTL out of range → 422
- minify() excludes None keys
"""

import json
import uuid
from datetime import datetime
import pytest
from pydantic import ValidationError

from src.api.models.envelope import Envelope, Sender, Recipient, create_sample_envelope


class TestEnvelopeValidation:
    """Test envelope schema validation."""
    
    def test_minimal_valid_envelope(self):
        """Test that minimal valid envelope passes validation."""
        envelope_data = {
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00.123Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }
        
        envelope = Envelope(**envelope_data)
        assert envelope.version == "1.0"  # Default value
        assert envelope.type == "message"  # Default value
        assert envelope.ttl_ms == 30000  # Default value
        assert envelope.message_id == envelope_data["message_id"]
        assert envelope.ts == envelope_data["ts"]
    
    def test_full_valid_envelope(self):
        """Test that envelope with all fields passes validation."""
        envelope_data = {
            "version": "1.0",
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            "type": "command",
            "sender": {"agent_id": "agent-001", "org_id": "org-123"},
            "recipient": {"agent_id": "agent-002", "org_id": "org-456"},
            "payload": {"action": "execute", "params": {"key": "value"}},
            "ttl_ms": 60000,
            "reply_to": "msg-reply-123",
            "nonce": "nonce-456"
        }
        
        envelope = Envelope(**envelope_data)
        assert envelope.version == "1.0"
        assert envelope.type == "command"
        assert envelope.ttl_ms == 60000
        assert envelope.reply_to == "msg-reply-123"
        assert envelope.nonce == "nonce-456"


class TestVersionValidation:
    """Test version field validation."""
    
    def test_valid_version(self):
        """Test that version 1.0 is accepted."""
        envelope_data = {
            "version": "1.0",
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }
        
        envelope = Envelope(**envelope_data)
        assert envelope.version == "1.0"
    
    def test_invalid_version(self):
        """Test that invalid version is rejected."""
        envelope_data = {
            "version": "2.0",
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Envelope(**envelope_data)
        
        errors = exc_info.value.errors()
        assert any("version" in str(error["loc"]) for error in errors)


class TestMessageIdValidation:
    """Test message_id field validation."""
    
    def test_valid_uuid4(self):
        """Test that valid UUID4 is accepted (approximating UUIDv7)."""
        message_id = str(uuid.uuid4())
        envelope_data = {
            "message_id": message_id,
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }
        
        # Note: Our current implementation accepts UUID4 as approximation
        # In production, this would need proper UUIDv7 validation
        envelope = Envelope(**envelope_data)
        assert envelope.message_id == message_id.lower()
    
    def test_invalid_uuid_format(self):
        """Test that invalid UUID format is rejected."""
        envelope_data = {
            "message_id": "not-a-uuid",
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Envelope(**envelope_data)
        
        errors = exc_info.value.errors()
        assert any("message_id" in str(error["loc"]) for error in errors)
    
    def test_empty_message_id(self):
        """Test that empty message_id is rejected."""
        envelope_data = {
            "message_id": "",
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }
        
        with pytest.raises(ValidationError):
            Envelope(**envelope_data)


class TestTimestampValidation:
    """Test timestamp field validation."""
    
    def test_valid_rfc3339_timestamps(self):
        """Test that valid RFC3339 timestamps are accepted."""
        valid_timestamps = [
            "2023-10-02T14:30:00Z",
            "2023-10-02T14:30:00.123Z",
            "2023-10-02T14:30:00.123456Z",
            "2023-12-31T23:59:59Z"
        ]
        
        for ts in valid_timestamps:
            envelope_data = {
                "message_id": str(uuid.uuid4()),
                "ts": ts,
                "sender": {"agent_id": "agent-001"},
                "recipient": {"agent_id": "agent-002"},
                "payload": {"action": "test"}
            }
            
            envelope = Envelope(**envelope_data)
            assert envelope.ts == ts
    
    def test_invalid_timestamp_formats(self):
        """Test that invalid timestamp formats are rejected."""
        invalid_timestamps = [
            "2023-10-02 14:30:00",  # Missing T
            "2023-10-02T14:30:00",  # Missing Z
            "2023-10-02T14:30:00+00:00",  # Timezone offset instead of Z
            "10/02/2023 14:30:00",  # Wrong format
            "not-a-timestamp",
            ""
        ]
        
        for ts in invalid_timestamps:
            envelope_data = {
                "message_id": str(uuid.uuid4()),
                "ts": ts,
                "sender": {"agent_id": "agent-001"},
                "recipient": {"agent_id": "agent-002"},
                "payload": {"action": "test"}
            }
            
            with pytest.raises(ValidationError) as exc_info:
                Envelope(**envelope_data)
            
            errors = exc_info.value.errors()
            assert any("ts" in str(error["loc"]) for error in errors)


class TestTypeValidation:
    """Test message type field validation."""
    
    def test_valid_types(self):
        """Test that all valid message types are accepted."""
        valid_types = ["message", "event", "command", "result", "error"]
        
        for msg_type in valid_types:
            envelope_data = {
                "message_id": str(uuid.uuid4()),
                "ts": "2023-10-02T14:30:00Z",
                "type": msg_type,
                "sender": {"agent_id": "agent-001"},
                "recipient": {"agent_id": "agent-002"},
                "payload": {"action": "test"}
            }
            
            envelope = Envelope(**envelope_data)
            assert envelope.type == msg_type
    
    def test_invalid_type(self):
        """Test that invalid message type is rejected."""
        envelope_data = {
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            "type": "invalid_type",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Envelope(**envelope_data)
        
        errors = exc_info.value.errors()
        assert any("type" in str(error["loc"]) for error in errors)


class TestSenderRecipientValidation:
    """Test sender and recipient field validation."""
    
    def test_valid_sender_recipient(self):
        """Test that valid sender/recipient are accepted."""
        envelope_data = {
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001", "org_id": "org-123"},
            "recipient": {"agent_id": "agent-002", "org_id": "org-456"},
            "payload": {"action": "test"}
        }
        
        envelope = Envelope(**envelope_data)
        assert envelope.sender.agent_id == "agent-001"
        assert envelope.sender.org_id == "org-123"
        assert envelope.recipient.agent_id == "agent-002"
        assert envelope.recipient.org_id == "org-456"
    
    def test_sender_without_org_id(self):
        """Test that sender without org_id is accepted."""
        envelope_data = {
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }
        
        envelope = Envelope(**envelope_data)
        assert envelope.sender.agent_id == "agent-001"
        assert envelope.sender.org_id is None
    
    def test_missing_agent_id(self):
        """Test that missing agent_id is rejected."""
        envelope_data = {
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"org_id": "org-123"},  # Missing agent_id
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Envelope(**envelope_data)
        
        errors = exc_info.value.errors()
        assert any("agent_id" in str(error["loc"]) for error in errors)
    
    def test_empty_agent_id(self):
        """Test that empty agent_id is rejected."""
        envelope_data = {
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": ""},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }
        
        with pytest.raises(ValidationError):
            Envelope(**envelope_data)


class TestTtlValidation:
    """Test TTL field validation."""
    
    def test_valid_ttl_values(self):
        """Test that valid TTL values are accepted."""
        valid_ttls = [1, 1000, 30000, 60000, 120000]
        
        for ttl in valid_ttls:
            envelope_data = {
                "message_id": str(uuid.uuid4()),
                "ts": "2023-10-02T14:30:00Z",
                "sender": {"agent_id": "agent-001"},
                "recipient": {"agent_id": "agent-002"},
                "payload": {"action": "test"},
                "ttl_ms": ttl
            }
            
            envelope = Envelope(**envelope_data)
            assert envelope.ttl_ms == ttl
    
    def test_ttl_out_of_range(self):
        """Test that TTL values out of range are rejected."""
        invalid_ttls = [0, -1, 120001, 999999]
        
        for ttl in invalid_ttls:
            envelope_data = {
                "message_id": str(uuid.uuid4()),
                "ts": "2023-10-02T14:30:00Z",
                "sender": {"agent_id": "agent-001"},
                "recipient": {"agent_id": "agent-002"},
                "payload": {"action": "test"},
                "ttl_ms": ttl
            }
            
            with pytest.raises(ValidationError) as exc_info:
                Envelope(**envelope_data)
            
            errors = exc_info.value.errors()
            assert any("ttl_ms" in str(error["loc"]) for error in errors)


class TestExtraFieldsValidation:
    """Test that extra fields are forbidden."""
    
    def test_extra_fields_rejected(self):
        """Test that extra fields in envelope are rejected."""
        envelope_data = {
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"},
            "extra_field": "not_allowed"  # Extra field
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Envelope(**envelope_data)
        
        errors = exc_info.value.errors()
        assert any("extra_field" in str(error["loc"]) for error in errors)
    
    def test_extra_fields_in_sender(self):
        """Test that extra fields in sender are rejected."""
        envelope_data = {
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            "sender": {
                "agent_id": "agent-001",
                "extra_field": "not_allowed"
            },
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            Envelope(**envelope_data)
        
        errors = exc_info.value.errors()
        assert any("extra_field" in str(error["loc"]) for error in errors)


class TestMinifyFunction:
    """Test the minify() helper function."""
    
    def test_minify_removes_none_values(self):
        """Test that minify() removes None values."""
        envelope_data = {
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
            # reply_to and nonce will be None by default
        }
        
        envelope = Envelope(**envelope_data)
        minified = envelope.minify()
        
        # None values should be removed
        assert "reply_to" not in minified
        assert "nonce" not in minified
        assert "org_id" not in minified["sender"]
        assert "org_id" not in minified["recipient"]
        
        # Non-None values should be present
        assert "message_id" in minified
        assert "version" in minified
        assert "type" in minified
        assert "ttl_ms" in minified
    
    def test_minify_preserves_non_none_values(self):
        """Test that minify() preserves non-None values."""
        envelope_data = {
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001", "org_id": "org-123"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"},
            "reply_to": "msg-reply-123"
        }
        
        envelope = Envelope(**envelope_data)
        minified = envelope.minify()
        
        # Non-None values should be preserved
        assert minified["reply_to"] == "msg-reply-123"
        assert minified["sender"]["org_id"] == "org-123"
        
        # None values should be removed
        assert "nonce" not in minified
        assert "org_id" not in minified["recipient"]
    
    def test_minify_nested_structures(self):
        """Test that minify() handles nested None values."""
        envelope_data = {
            "message_id": str(uuid.uuid4()),
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {
                "action": "test",
                "params": {
                    "key1": "value1",
                    "key2": None,
                    "key3": "value3"
                },
                "optional": None
            }
        }
        
        envelope = Envelope(**envelope_data)
        minified = envelope.minify()
        
        # Nested None values should be removed
        assert "key2" not in minified["payload"]["params"]
        assert "optional" not in minified["payload"]
        
        # Non-None nested values should be preserved
        assert minified["payload"]["params"]["key1"] == "value1"
        assert minified["payload"]["params"]["key3"] == "value3"


class TestCreateSampleEnvelope:
    """Test the create_sample_envelope helper function."""
    
    def test_create_sample_envelope_defaults(self):
        """Test that create_sample_envelope creates valid envelope with defaults."""
        envelope = create_sample_envelope()
        
        assert envelope.sender.agent_id == "agent-001"
        assert envelope.recipient.agent_id == "agent-002"
        assert envelope.payload == {"action": "test", "data": "sample"}
        assert envelope.version == "1.0"
        assert envelope.type == "message"
    
    def test_create_sample_envelope_custom_params(self):
        """Test that create_sample_envelope accepts custom parameters."""
        custom_payload = {"custom": "data"}
        envelope = create_sample_envelope(
            sender_agent_id="custom-sender",
            recipient_agent_id="custom-recipient",
            payload=custom_payload
        )
        
        assert envelope.sender.agent_id == "custom-sender"
        assert envelope.recipient.agent_id == "custom-recipient"
        assert envelope.payload == custom_payload
