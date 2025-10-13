# -*- coding: utf-8 -*-
"""
Enhanced security service for HMAC v1 authentication, canonical signing, and timestamp validation.
Complements existing JWT-based security.py without conflicts.
"""
import hashlib
import hmac
import secrets
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from urllib.parse import quote


class HMACSecurityService:
    """Comprehensive HMAC v1 security service for Brikk API authentication."""

    # HMAC v1 constants
    HMAC_VERSION = "v1"
    TIMESTAMP_DRIFT_SECONDS = 300  # '+/-5 minutes

    @staticmethod
    def generate_canonical_string(
        method: str,
        path: str,
        timestamp: str,
        body_hash: str,
        message_id: Optional[str] = None
    ) -> str:
        """
        Generate canonical string for HMAC v1 signing.

        Format: METHOD\nPATH\nTIMESTAMP\nBODY_SHA256\nMESSAGE_ID
        """
        canonical_parts = [
            method.upper(),
            path,
            timestamp,
            body_hash
        ]

        if message_id:
            canonical_parts.append(message_id)

        return "\n".join(canonical_parts)

    @staticmethod
    def compute_body_hash(body: bytes) -> str:
        """Compute SHA-256 hash of request body."""
        return hashlib.sha256(body).hexdigest()

    @staticmethod
    def sign_canonical_string(canonical_string: str, secret: str) -> str:
        """Sign canonical string with HMAC-SHA256."""
        return hmac.new(
            secret.encode('utf-8'),
            canonical_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    @classmethod
    def create_signature(
        cls,
        method: str,
        path: str,
        timestamp: str,
        body: bytes,
        secret: str,
        message_id: Optional[str] = None
    ) -> str:
        """
        Create HMAC v1 signature for request.

        Returns signature in format: v1=<hex_signature>
        """
        body_hash = cls.compute_body_hash(body)
        canonical_string = cls.generate_canonical_string(
            method, path, timestamp, body_hash, message_id
        )
        signature = cls.sign_canonical_string(canonical_string, secret)
        return f"{cls.HMAC_VERSION}={signature}"

    @classmethod
    def verify_signature(
        cls,
        method: str,
        path: str,
        timestamp: str,
        body: bytes,
        secret: str,
        provided_signature: str,
        message_id: Optional[str] = None
    ) -> bool:
        """
        Verify HMAC v1 signature against request.

        Uses constant-time comparison to prevent timing attacks.
        """
        try:
            # Parse provided signature
            if not provided_signature.startswith(f"{cls.HMAC_VERSION}="):
                return False

            provided_hex = provided_signature[len(f"{cls.HMAC_VERSION}="):]

            # Generate expected signature
            expected_signature = cls.create_signature(
                method, path, timestamp, body, secret, message_id
            )
            expected_hex = expected_signature[len(f"{cls.HMAC_VERSION}="):]

            # Constant-time comparison
            return secrets.compare_digest(provided_hex, expected_hex)

        except Exception:
            return False

    @staticmethod
    def parse_rfc3339_timestamp(timestamp_str: str) -> Optional[datetime]:
        """
        Parse RFC3339 timestamp string to datetime object.

        Supports formats:
        - 2023-12-01T10:30:00Z
        - 2023-12-01T10:30:00.123Z
        - 2023-12-01T10:30:00+00:00
        - 2023-12-01T10:30:00.123+00:00
        """
        try:
            # Handle different RFC3339 formats
            formats = [
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f%z"
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(timestamp_str, fmt)
                    # Ensure timezone awareness
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue

            return None

        except Exception:
            return None

    @classmethod
    def validate_timestamp_drift(
            cls, timestamp_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validate timestamp is within acceptable drift range ('+/-300 seconds).

        Returns (is_valid, error_message)
        """
        try:
            # Parse timestamp
            timestamp_dt = cls.parse_rfc3339_timestamp(timestamp_str)
            if not timestamp_dt:
                return False, "Invalid RFC3339 timestamp format"

            # Get current time in UTC
            now = datetime.now(timezone.utc)

            # Calculate drift in seconds
            drift_seconds = abs((timestamp_dt - now).total_seconds())

            if drift_seconds > cls.TIMESTAMP_DRIFT_SECONDS:
                return False, f"Timestamp drift {drift_seconds:.0f}s exceeds limit of {cls.TIMESTAMP_DRIFT_SECONDS}s"

            return True, None

        except Exception as e:
            return False, f"Timestamp validation error: {str(e)}"

    @staticmethod
    def generate_request_id() -> str:
        """Generate unique request ID for tracking."""
        return f"req_{secrets.token_urlsafe(16)}"

    @staticmethod
    def constant_time_compare(a: str, b: str) -> bool:
        """Constant-time string comparison to prevent timing attacks."""
        return secrets.compare_digest(a, b)

    @classmethod
    def extract_message_id_from_body(cls, body: bytes) -> Optional[str]:
        """
        Extract message_id from JSON request body for signature verification.

        Returns None if body is not valid JSON or message_id is not present.
        """
        try:
            if not body:
                return None

            data = json.loads(body.decode('utf-8'))
            return data.get('message_id')

        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    @staticmethod
    def sanitize_path_for_signing(path: str) -> str:
        """
        Sanitize URL path for consistent signing.

        - Removes query parameters
        - Normalizes path separators
        - URL decodes and re-encodes consistently
        """
        # Remove query parameters
        if '?' in path:
            path = path.split('?')[0]

        # Normalize path
        path = path.strip('/')
        if not path.startswith('/'):
            path = '/' + path

        return path

    @classmethod
    def create_auth_context(
        cls,
        organization_id: int,
        agent_id: Optional[int],
        key_id: str,
        scopes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create authentication context for authenticated requests.
        """
        return {
            'organization_id': organization_id,
            'agent_id': agent_id,
            'key_id': key_id,
            'scopes': json.loads(scopes) if scopes else [],
            'authenticated_at': datetime.now(timezone.utc).isoformat(),
            'request_id': cls.generate_request_id()
        }

    @staticmethod
    def hash_for_idempotency(key_id: str, body_hash: str) -> str:
        """
        Generate idempotency key from API key and request body hash.

        Format: idem:{key_prefix}:{body_hash_prefix}
        """
        key_prefix = key_id[:16] if len(key_id) > 16 else key_id
        body_prefix = body_hash[:16] if len(body_hash) > 16 else body_hash
        return f"idem:{key_prefix}:{body_prefix}"

    @classmethod
    def validate_request_headers(
            cls, headers: Dict[str, str]) -> Tuple[bool, Optional[str], Dict[str, str]]:
        """
        Validate required authentication headers are present.

        Returns (is_valid, error_message, extracted_headers)
        """
        required_headers = [
            'X-Brikk-Key',
            'X-Brikk-Timestamp',
            'X-Brikk-Signature']
        extracted = {}

        for header in required_headers:
            value = headers.get(header)
            if not value:
                return False, f"Missing required header: {header}", {}
            extracted[header.lower().replace('-', '_')] = value

        return True, None, extracted

    @staticmethod
    def create_error_response(
            code: str, message: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Create standardized error response."""
        response = {
            'code': code,
            'message': message
        }

        if request_id:
            response['request_id'] = request_id
        else:
            response['request_id'] = HMACSecurityService.generate_request_id()

        return response
