# -*- coding: utf-8 -*-
"""Main Brikk SDK client."""

import os
from typing import Optional

from ._http import HTTPClient
from .resources import (
    AgentsResource,
    CoordinationResource,
    EconomyResource,
    HealthResource,
    ReputationResource,
)


class BrikkClient:
    """Brikk API client.

    The main entry point for interacting with the Brikk platform.

    Args:
        base_url: Base URL of the Brikk API (default: from BRIKK_BASE_URL env var or http://localhost:8000)
        api_key: API key for authentication (default: from BRIKK_API_KEY env var)
        signing_secret: Signing secret for HMAC authentication (default: from BRIKK_SIGNING_SECRET env var)
        org_id: Default organization ID for requests (optional)
        timeout: Request timeout in seconds (default: 30)
        max_retries: Maximum number of retries for failed requests (default: 3)

    Example:
        >>> from brikk import BrikkClient
        >>> client = BrikkClient(
        ...     base_url="https://api.getbrikk.com",
        ...     api_key="your-api-key"
        ... )
        >>> health = client.health.ping()
        >>> print(health['status'])
        'ok'
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        signing_secret: Optional[str] = None,
        org_id: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.base_url = base_url or os.getenv("BRIKK_BASE_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("BRIKK_API_KEY")
        self.signing_secret = signing_secret or os.getenv("BRIKK_SIGNING_SECRET")
        self.org_id = org_id or os.getenv("BRIKK_ORG_ID")
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize HTTP client
        self._http = HTTPClient(
            base_url=self.base_url,
            api_key=self.api_key,
            signing_secret=self.signing_secret,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

        # Initialize resource accessors
        self.health = HealthResource(self._http)
        self.agents = AgentsResource(self._http)
        self.coordination = CoordinationResource(self._http)
        self.economy = EconomyResource(self._http)
        self.reputation = ReputationResource(self._http)

    def __repr__(self) -> str:
        return f"BrikkClient(base_url={self.base_url!r})"

