# -*- coding: utf-8 -*-
"""Health check resources."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .._http import HTTPClient

from ..types import HealthStatus


class HealthResource:
    """Health check operations."""

    def __init__(self, http_client: "HTTPClient"):
        self._http = http_client

    def ping(self) -> HealthStatus:
        """Check if the API is responsive.

        Returns:
            Health status dict with 'status' field

        Example:
            >>> client.health.ping()
            {'status': 'ok'}
        """
        return self._http.get("/healthz")

    def readiness(self) -> HealthStatus:
        """Check if the API is ready to serve requests.

        Returns:
            Readiness status dict

        Example:
            >>> client.health.readiness()
            {'status': 'ready'}
        """
        return self._http.get("/readyz")

    def coordination_health(self) -> HealthStatus:
        """Check coordination service health.

        Returns:
            Coordination service health status

        Example:
            >>> client.health.coordination_health()
            {'status': 'ok', 'service': 'coordination'}
        """
        return self._http.get("/api/v1/coordination/health")

