# -*- coding: utf-8 -*-
"""
Test suite for envelope UUID validation with environment flag.

Tests both strict UUIDv7 mode and UUID4 compatibility mode.
"""

import os
import uuid
import pytest
from pydantic import ValidationError

from src.schemas.envelope import Envelope


class TestUUIDValidationModes:
    """Test UUID validation with BRIKK_ALLOW_UUID4 environment flag."""

    def test_uuidv7_always_accepted(self):
        """Test that UUIDv7 is always accepted regardless of env flag."""
        # Note: This is a mock UUIDv7 - in production you'd use a proper UUIDv7 library
        # For testing, we'll create a UUID with version 7 bits set
        mock_uuidv7 = "01234567-89ab-7def-8123-456789abcdef"  # Version 7 in 13th hex digit

        envelope_data = {
            "message_id": mock_uuidv7,
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }

        # Should work with flag disabled (default)
        os.environ.pop("BRIKK_ALLOW_UUID4", None)
        envelope = Envelope(**envelope_data)
        assert envelope.message_id == mock_uuidv7.lower()

        # Should also work with flag enabled
        os.environ["BRIKK_ALLOW_UUID4"] = "true"
        envelope = Envelope(**envelope_data)
        assert envelope.message_id == mock_uuidv7.lower()

        # Clean up
        os.environ.pop("BRIKK_ALLOW_UUID4", None)

    def test_uuid4_rejected_by_default(self):
        """Test that UUID4 is rejected when BRIKK_ALLOW_UUID4 is false (default)."""
        uuid4_str = str(uuid.uuid4())
        envelope_data = {
            "message_id": uuid4_str,
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }

        # Ensure flag is not set (default behavior)
        os.environ.pop("BRIKK_ALLOW_UUID4", None)

        with pytest.raises(ValidationError) as exc_info:
            Envelope(**envelope_data)

        errors = exc_info.value.errors()
        assert any("message_id" in str(error["loc"]) for error in errors)
        assert any("UUIDv7" in str(error["msg"]) for error in errors)
        assert any(
            "BRIKK_ALLOW_UUID4=true" in str(
                error["msg"]) for error in errors)

    def test_uuid4_accepted_when_flag_enabled(self):
        """Test that UUID4 is accepted when BRIKK_ALLOW_UUID4=true."""
        uuid4_str = str(uuid.uuid4())
        envelope_data = {
            "message_id": uuid4_str,
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }

        # Enable UUID4 compatibility
        os.environ["BRIKK_ALLOW_UUID4"] = "true"

        try:
            envelope = Envelope(**envelope_data)
            assert envelope.message_id == uuid4_str.lower()
        finally:
            # Clean up
            os.environ.pop("BRIKK_ALLOW_UUID4", None)

    def test_uuid4_rejected_when_flag_explicitly_false(self):
        """Test that UUID4 is rejected when BRIKK_ALLOW_UUID4=false."""
        uuid4_str = str(uuid.uuid4())
        envelope_data = {
            "message_id": uuid4_str,
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }

        # Explicitly disable UUID4 compatibility
        os.environ["BRIKK_ALLOW_UUID4"] = "false"

        try:
            with pytest.raises(ValidationError) as exc_info:
                Envelope(**envelope_data)

            errors = exc_info.value.errors()
            assert any("message_id" in str(error["loc"]) for error in errors)
            assert any("UUIDv7" in str(error["msg"]) for error in errors)
        finally:
            # Clean up
            os.environ.pop("BRIKK_ALLOW_UUID4", None)

    def test_invalid_uuid_versions_rejected(self):
        """Test that UUID versions other than 4 and 7 are always rejected."""
        # Create UUIDs with different versions
        uuid_v1 = str(uuid.uuid1())  # Version 1
        uuid_v3 = str(uuid.uuid3(uuid.NAMESPACE_DNS, 'test'))  # Version 3
        uuid_v5 = str(uuid.uuid5(uuid.NAMESPACE_DNS, 'test'))  # Version 5

        invalid_uuids = [uuid_v1, uuid_v3, uuid_v5]

        for invalid_uuid in invalid_uuids:
            envelope_data = {
                "message_id": invalid_uuid,
                "ts": "2023-10-02T14:30:00Z",
                "sender": {"agent_id": "agent-001"},
                "recipient": {"agent_id": "agent-002"},
                "payload": {"action": "test"}
            }

            # Should fail even with UUID4 flag enabled
            os.environ["BRIKK_ALLOW_UUID4"] = "true"

            try:
                with pytest.raises(ValidationError) as exc_info:
                    Envelope(**envelope_data)

                errors = exc_info.value.errors()
                assert any(
                    "message_id" in str(
                        error["loc"]) for error in errors)
            finally:
                # Clean up
                os.environ.pop("BRIKK_ALLOW_UUID4", None)

    def test_env_flag_case_insensitive(self):
        """Test that environment flag is case insensitive."""
        uuid4_str = str(uuid.uuid4())
        envelope_data = {
            "message_id": uuid4_str,
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }

        # Test various case combinations
        true_values = ["true", "TRUE", "True", "tRuE"]

        for true_val in true_values:
            os.environ["BRIKK_ALLOW_UUID4"] = true_val

            try:
                envelope = Envelope(**envelope_data)
                assert envelope.message_id == uuid4_str.lower()
            finally:
                os.environ.pop("BRIKK_ALLOW_UUID4", None)

    def test_env_flag_invalid_values_treated_as_false(self):
        """Test that invalid environment flag values are treated as false."""
        uuid4_str = str(uuid.uuid4())
        envelope_data = {
            "message_id": uuid4_str,
            "ts": "2023-10-02T14:30:00Z",
            "sender": {"agent_id": "agent-001"},
            "recipient": {"agent_id": "agent-002"},
            "payload": {"action": "test"}
        }

        # Test invalid values
        invalid_values = ["yes", "1", "on", "enable", "invalid"]

        for invalid_val in invalid_values:
            os.environ["BRIKK_ALLOW_UUID4"] = invalid_val

            try:
                with pytest.raises(ValidationError):
                    Envelope(**envelope_data)
            finally:
                os.environ.pop("BRIKK_ALLOW_UUID4", None)
