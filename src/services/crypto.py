# src/services/crypto.py
import hashlib
import os
import secrets
from typing import Tuple


def generate_api_key() -> str:
    """Generate a new API key with brikk_ prefix"""
    random_part = secrets.token_urlsafe(32)  # 32 bytes = 43 chars base64url
    return f"brikk_{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using PBKDF2 with SHA-256.
    Returns the hash in the format: salt$hash
    """
    # Generate a random salt
    salt = os.urandom(32)  # 32 bytes salt
    
    # Hash the API key with PBKDF2
    key_hash = hashlib.pbkdf2_hmac(
        'sha256',           # Hash algorithm
        api_key.encode(),   # API key as bytes
        salt,               # Salt
        100000              # Iterations (100k is recommended minimum)
    )
    
    # Return salt and hash as hex, separated by $
    return f"{salt.hex()}${key_hash.hex()}"


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """
    Verify an API key against its stored hash.
    Returns True if the API key matches the hash.
    """
    try:
        # Split the stored hash into salt and hash
        salt_hex, hash_hex = stored_hash.split('$', 1)
        salt = bytes.fromhex(salt_hex)
        stored_key_hash = bytes.fromhex(hash_hex)
        
        # Hash the provided API key with the same salt
        key_hash = hashlib.pbkdf2_hmac(
            'sha256',
            api_key.encode(),
            salt,
            100000
        )
        
        # Compare hashes using constant-time comparison
        return secrets.compare_digest(key_hash, stored_key_hash)
    
    except (ValueError, TypeError):
        # Invalid hash format
        return False


def generate_and_hash_api_key() -> Tuple[str, str]:
    """
    Generate a new API key and return both the plaintext key and its hash.
    Returns: (plaintext_api_key, hashed_api_key)
    """
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    return api_key, api_key_hash
