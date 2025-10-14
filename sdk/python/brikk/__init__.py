# -*- coding: utf-8 -*-
"""Brikk Python SDK.

Official Python SDK for the Brikk AI-to-AI infrastructure platform.

Example:
    >>> from brikk import BrikkClient
    >>> client = BrikkClient(api_key="your-api-key")
    >>> health = client.health.ping()
"""

from .client import BrikkClient
from .errors import (
    AuthError,
    BrikkError,
    HTTPError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
)
from .types import (
    Agent,
    CoordinationMessage,
    HealthStatus,
    ReputationScore,
    Transaction,
)

__version__ = "0.1.0"
__all__ = [
    "BrikkClient",
    # Errors
    "BrikkError",
    "HTTPError",
    "AuthError",
    "RateLimitError",
    "ServerError",
    "ValidationError",
    "NotFoundError",
    "TimeoutError",
    # Types
    "Agent",
    "CoordinationMessage",
    "HealthStatus",
    "ReputationScore",
    "Transaction",
]

