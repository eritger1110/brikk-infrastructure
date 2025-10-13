"""""
Service for managing Prometheus metrics.

Provides a centralized service for creating, registering, and collecting metrics.
Also includes middleware for automatically recording HTTP request metrics.
"""

import os
import time
from typing import Optional
from flask import Flask, request, g, current_app, has_app_context
from prometheus_client import REGISTRY, CollectorRegistry, Counter, Histogram, Gauge
from prometheus_client.exposition import generate_latest

def init_metrics(app: Flask) -> None:
    """Initialize metrics service and endpoints."""
    service = MetricsService()
    app.extensions['metrics'] = service

    if service.enabled:
        # Add middleware to record HTTP requests
        @app.before_request
        def before_request():
            g.start_time = time.time()

        @app.after_request
        def after_request(response):
            duration = time.time() - g.start_time
            service.record_http_request(
                route=request.path,
                method=request.method,
                status_code=response.status_code,
                duration_seconds=duration
            )
            return response

        # Add /metrics endpoint
        @app.route("/metrics")
        def metrics():
            return generate_latest(service.registry), 200, {'Content-Type': 'text/plain; version=0.0.4; charset=utf-8'}

def get_metrics_service() -> Optional['MetricsService']:
    """Get the metrics service instance from the current app context."""
    if has_app_context():
        return current_app.extensions.get('metrics')
    return None

class MetricsService:
    """Service for managing Prometheus metrics."""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """Initialize the metrics service."""
        self.enabled = os.environ.get("BRIKK_METRICS_ENABLED", "true").lower() == "true"
        self.registry = registry if registry is not None else REGISTRY

        if self.enabled:
            self.http_requests_total = Counter(
                "brikk_http_requests_total",
                "Total number of HTTP requests.",
                ["route", "method", "status"],
                registry=self.registry
            )
            self.http_request_duration_seconds = Histogram(
                "brikk_http_request_duration_seconds",
                "Duration of HTTP requests in seconds.",
                ["route", "method"],
                registry=self.registry
            )
            self.http_errors_total = Counter(
                "brikk_http_errors_total",
                "Total number of HTTP errors.",
                ["route", "kind"],
                registry=self.registry
            )
            self.rate_limit_hits_total = Counter(
                "brikk_rate_limit_hits_total",
                "Total number of rate limit hits.",
                ["scope"],
                registry=self.registry
            )
            self.idempotency_replays_total = Counter(
                "brikk_idempotency_replays_total",
                "Total number of idempotency replays.",
                registry=self.registry
            )
            self.redis_up = Gauge(
                "brikk_redis_up",
                "Redis connection status (1 for up, 0 for down).",
                registry=self.registry
            )
            self.feature_flags = Gauge(
                "brikk_feature_flag",
                "Status of feature flags (1 for enabled, 0 for disabled).",
                ["flag", "enabled"],
                registry=self.registry
            )

    def record_http_request(self, route: str, method: str, status_code: int, duration_seconds: float):
        """Record an HTTP request."""
        if self.enabled:
            normalized_route = self._normalize_route(route)
            self.http_requests_total.labels(route=normalized_route, method=method, status=status_code).inc()
            self.http_request_duration_seconds.labels(route=normalized_route, method=method).observe(duration_seconds)

    def get_metrics(self) -> str:
        """Get metrics data as text."""
        if self.enabled:
            return generate_latest(self.registry).decode('utf-8')
        return ""

    def _normalize_route(self, route: str) -> str:
        parts = route.split('/')
        for i, part in enumerate(parts):
            if part.isdigit():
                parts[i] = '{id}'
            try:
                import uuid
                uuid.UUID(part)
                parts[i] = '{uuid}'
            except (ValueError, AttributeError):
                pass
        return '/'.join(parts)

