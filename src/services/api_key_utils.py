# -*- coding: utf-8 -*-
"""
API Key utilities for Stage 5 API Gateway.

Handles generation, hashing, and validation of scoped API keys.
Supports both live (brk_live_*) and test (brk_test_*) key prefixes.
"""
import secrets
import hashlib
from typing import Tuple


class APIKeyUtils:
    """Utilities for API key generation and validation."""
    
    # Key prefixes
    PREFIX_LIVE = "brk_live_"
    PREFIX_TEST = "brk_test_"
    
    # Key format: prefix + 32 random bytes (hex) = prefix + 64 chars
    KEY_RANDOM_BYTES = 32
    
    @classmethod
    def generate_key(cls, is_test: bool = False) -> str:
        """
        Generate a new API key with appropriate prefix.
        
        Args:
            is_test: If True, generates test key (brk_test_*), otherwise live key (brk_live_*)
            
        Returns:
            API key string in format: brk_live_<64_hex_chars> or brk_test_<64_hex_chars>
            
        Example:
            >>> key = APIKeyUtils.generate_key(is_test=False)
            >>> key.startswith('brk_live_')
            True
            >>> len(key)
            73  # 9 (prefix) + 64 (hex)
        """
        prefix = cls.PREFIX_TEST if is_test else cls.PREFIX_LIVE
        random_part = secrets.token_hex(cls.KEY_RANDOM_BYTES)
        return f"{prefix}{random_part}"
    
    @classmethod
    def hash_key(cls, api_key: str) -> str:
        """
        Hash an API key using SHA-256.
        
        Args:
            api_key: The plaintext API key
            
        Returns:
            Hex-encoded SHA-256 hash of the key
            
        Note:
            We use SHA-256 (not PBKDF2) because:
            1. API keys are high-entropy (256 bits)
            2. No need for slow hashing (unlike passwords)
            3. Faster verification for high-throughput API
        """
        return hashlib.sha256(api_key.encode('utf-8')).hexdigest()
    
    @classmethod
    def verify_key(cls, provided_key: str, stored_hash: str) -> bool:
        """
        Verify an API key against its stored hash.
        
        Args:
            provided_key: The API key provided in the request
            stored_hash: The stored hash from the database
            
        Returns:
            True if the key matches the hash, False otherwise
            
        Uses constant-time comparison to prevent timing attacks.
        """
        computed_hash = cls.hash_key(provided_key)
        return secrets.compare_digest(computed_hash, stored_hash)
    
    @classmethod
    def is_valid_format(cls, api_key: str) -> bool:
        """
        Check if an API key has valid format.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            True if the key has valid format (correct prefix and length)
        """
        if not api_key:
            return False
            
        # Check prefix
        if not (api_key.startswith(cls.PREFIX_LIVE) or api_key.startswith(cls.PREFIX_TEST)):
            return False
        
        # Check length: prefix (9 or 10) + 64 hex chars
        expected_len_live = len(cls.PREFIX_LIVE) + (cls.KEY_RANDOM_BYTES * 2)
        expected_len_test = len(cls.PREFIX_TEST) + (cls.KEY_RANDOM_BYTES * 2)
        
        return len(api_key) in (expected_len_live, expected_len_test)
    
    @classmethod
    def is_test_key(cls, api_key: str) -> bool:
        """Check if an API key is a test key."""
        return api_key.startswith(cls.PREFIX_TEST)
    
    @classmethod
    def is_live_key(cls, api_key: str) -> bool:
        """Check if an API key is a live key."""
        return api_key.startswith(cls.PREFIX_LIVE)
    
    @classmethod
    def generate_key_pair(cls) -> Tuple[str, str]:
        """
        Generate a live key and return both the key and its hash.
        
        Returns:
            Tuple of (api_key, key_hash)
            
        Example:
            >>> key, key_hash = APIKeyUtils.generate_key_pair()
            >>> APIKeyUtils.verify_key(key, key_hash)
            True
        """
        key = cls.generate_key(is_test=False)
        key_hash = cls.hash_key(key)
        return key, key_hash

