# -*- coding: utf-8 -*-
"""
API Gateway Metrics Extension.

Extends the base metrics service with API Gateway specific metrics:
- Authentication method tracking
- Rate limit events
- Tier-based request tracking
- OAuth token generation/verification
"""
from prometheus_client import Counter, Histogram, Gauge
from flask import g, request
from typing import Optional


class GatewayMetrics:
    """API Gateway specific metrics."""
    
    def __init__(self, registry):
        """Initialize gateway metrics."""
        self.registry = registry
        
        # Authentication metrics
        self.auth_requests_total = Counter(
            "brikk_auth_requests_total",
            "Total authentication attempts",
            ["method", "status"],
            registry=self.registry
        )
        
        self.auth_failures_total = Counter(
            "brikk_auth_failures_total",
            "Total authentication failures",
            ["method", "reason"],
            registry=self.registry
        )
        
        # Rate limiting metrics
        self.rate_limit_exceeded_total = Counter(
            "brikk_rate_limit_exceeded_total",
            "Total rate limit exceeded events",
            ["tier", "endpoint"],
            registry=self.registry
        )
        
        self.rate_limit_remaining = Gauge(
            "brikk_rate_limit_remaining",
            "Remaining requests in current window",
            ["actor_id", "tier"],
            registry=self.registry
        )
        
        # Request tracking by tier
        self.requests_by_tier_total = Counter(
            "brikk_requests_by_tier_total",
            "Total requests by tier",
            ["tier", "endpoint"],
            registry=self.registry
        )
        
        # OAuth metrics
        self.oauth_tokens_issued_total = Counter(
            "brikk_oauth_tokens_issued_total",
            "Total OAuth tokens issued",
            ["client_id"],
            registry=self.registry
        )
        
        self.oauth_token_verifications_total = Counter(
            "brikk_oauth_token_verifications_total",
            "Total OAuth token verifications",
            ["status"],
            registry=self.registry
        )
        
        # API key metrics
        self.api_key_usage_total = Counter(
            "brikk_api_key_usage_total",
            "Total API key usage",
            ["key_id", "org_id"],
            registry=self.registry
        )
        
        # Latency by auth method
        self.auth_latency_seconds = Histogram(
            "brikk_auth_latency_seconds",
            "Authentication latency in seconds",
            ["method"],
            registry=self.registry
        )
    
    def record_auth_attempt(self, method: str, success: bool, reason: Optional[str] = None):
        """Record an authentication attempt."""
        status = "success" if success else "failure"
        self.auth_requests_total.labels(method=method, status=status).inc()
        
        if not success and reason:
            self.auth_failures_total.labels(method=method, reason=reason).inc()
    
    def record_rate_limit_exceeded(self, tier: str, endpoint: str):
        """Record a rate limit exceeded event."""
        self.rate_limit_exceeded_total.labels(tier=tier, endpoint=endpoint).inc()
    
    def record_request_by_tier(self, tier: str, endpoint: str):
        """Record a request by tier."""
        self.requests_by_tier_total.labels(tier=tier, endpoint=endpoint).inc()
    
    def record_oauth_token_issued(self, client_id: str):
        """Record an OAuth token issuance."""
        self.oauth_tokens_issued_total.labels(client_id=client_id).inc()
    
    def record_oauth_token_verification(self, success: bool):
        """Record an OAuth token verification."""
        status = "valid" if success else "invalid"
        self.oauth_token_verifications_total.labels(status=status).inc()
    
    def record_api_key_usage(self, key_id: str, org_id: str):
        """Record API key usage."""
        self.api_key_usage_total.labels(key_id=key_id, org_id=org_id).inc()
    
    def record_auth_latency(self, method: str, duration_seconds: float):
        """Record authentication latency."""
        self.auth_latency_seconds.labels(method=method).observe(duration_seconds)


def init_gateway_metrics(app):
    """
    Initialize API Gateway metrics.
    
    Args:
        app: Flask application instance
    """
    # Get existing metrics service
    metrics_service = app.extensions.get('metrics')
    
    if metrics_service and metrics_service.enabled:
        # Add gateway metrics to the service
        gateway_metrics = GatewayMetrics(metrics_service.registry)
        app.extensions['gateway_metrics'] = gateway_metrics
        
        # Add middleware to track tier-based requests
        @app.after_request
        def track_tier_requests(response):
            if hasattr(g, 'tier') and hasattr(g, 'endpoint'):
                gateway_metrics.record_request_by_tier(
                    tier=g.tier,
                    endpoint=request.endpoint or 'unknown'
                )
            return response


def get_gateway_metrics():
    """Get the gateway metrics instance from the current app context."""
    from flask import current_app, has_app_context
    
    if has_app_context():
        return current_app.extensions.get('gateway_metrics')
    return None

