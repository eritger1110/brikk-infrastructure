
"""
Prometheus metrics service for Brikk coordination API.

Provides comprehensive observability with counters, histograms, and gauges for:
- HTTP request metrics (total, duration, errors)
- Rate limiting metrics
- Idempotency metrics
- Redis connectivity
- Feature flag status

Metrics are exposed at /metrics endpoint when BRIKK_METRICS_ENABLED=true.
"""

import os
import time
from typing import Optional, Dict, Any
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
from flask import Flask, Response, request, g


class MetricsService:
    """Service for collecting and exposing Prometheus metrics."""
    
    def __init__(self, registry=REGISTRY):
        self.registry = registry
        self.enabled = self._get_feature_flag("BRIKK_METRICS_ENABLED", "true")
        
        if self.enabled:
            self._initialize_metrics()
    
    def _get_feature_flag(self, flag_name: str, default: str = "false") -> bool:
        """Get feature flag value from environment."""
        return os.environ.get(flag_name, default).lower() == "true"
    
    def _initialize_metrics(self):
        """Initialize all Prometheus metrics."""
        
        # HTTP Request Metrics
        self.http_requests_total = Counter(
            'brikk_http_requests_total',
            'Total HTTP requests processed',
            ['route', 'method', 'status'],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            'brikk_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['route', 'method'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        self.http_errors_total = Counter(
            'brikk_http_errors_total',
            'Total HTTP errors by type',
            ['route', 'kind'],
            registry=self.registry
        )
        
        # Rate Limiting Metrics
        self.rate_limit_hits_total = Counter(
            'brikk_rate_limit_hits_total',
            'Total rate limit hits',
            ['scope'],
            registry=self.registry
        )
        
        # Idempotency Metrics
        self.idempotency_replays_total = Counter(
            'brikk_idempotency_replays_total',
            'Total idempotent request replays',
            registry=self.registry
        )
        
        # Infrastructure Metrics
        self.redis_up = Gauge(
            'brikk_redis_up',
            'Redis connectivity status (1=up, 0=down)',
            registry=self.registry
        )
        
        # Feature Flag Metrics
        self.feature_flags = Gauge(
            'brikk_feature_flag',
            'Feature flag status (1=enabled, 0=disabled)',
            ['flag'],
            registry=self.registry
        )
        
        # Application Info
        self.app_info = Info(
            'brikk_app',
            'Application information',
            registry=self.registry
        )
        
        # Initialize app info
        self.app_info.info({
            'version': '1.0.0',
            'service': 'coordination-api',
            'environment': os.environ.get('FLASK_ENV', 'production')
        })
        
        # Initialize feature flag metrics
        self._update_feature_flag_metrics()
    
    def _update_feature_flag_metrics(self):
        """Update feature flag metrics with current values."""
        if not self.enabled:
            return
        
        feature_flags = {
            'per_org_keys': self._get_feature_flag("BRIKK_FEATURE_PER_ORG_KEYS"),
            'idempotency': self._get_feature_flag("BRIKK_IDEM_ENABLED", "true"),
            'rate_limiting': self._get_feature_flag("BRIKK_RLIMIT_ENABLED"),
            'uuid4_allowed': self._get_feature_flag("BRIKK_ALLOW_UUID4"),
            'metrics': self._get_feature_flag("BRIKK_METRICS_ENABLED", "true"),
            'json_logging': self._get_feature_flag("BRIKK_LOG_JSON", "true")
        }
        
        for flag, enabled in feature_flags.items():
            self.feature_flags.labels(flag=flag).set(1 if enabled else 0)
    
    def record_http_request(self, route: str, method: str, status_code: int, duration: float):
        """Record HTTP request metrics."""
        if not self.enabled:
            return
        
        # Record request count
        self.http_requests_total.labels(
            route=route,
            method=method,
            status=str(status_code)
        ).inc()
        
        # Record request duration
        self.http_request_duration_seconds.labels(
            route=route,
            method=method
        ).observe(duration)
        
        # Record errors for 4xx and 5xx status codes
        if status_code >= 400:
            error_kind = self._get_error_kind(status_code)
            self.http_errors_total.labels(
                route=route,
                kind=error_kind
            ).inc()
    
    def _get_error_kind(self, status_code: int) -> str:
        """Get error kind based on status code."""
        if 400 <= status_code < 500:
            error_kinds = {
                400: 'bad_request',
                401: 'unauthorized',
                403: 'forbidden',
                404: 'not_found',
                409: 'conflict',
                413: 'payload_too_large',
                415: 'unsupported_media_type',
                422: 'unprocessable_entity',
                429: 'rate_limited'
            }
            return error_kinds.get(status_code, 'client_error')
        elif 500 <= status_code < 600:
            return 'server_error'
        else:
            return 'unknown'
    
    def record_rate_limit_hit(self, scope: str):
        """Record rate limit hit."""
        if not self.enabled:
            return
        
        self.rate_limit_hits_total.labels(scope=scope).inc()
    
    def record_idempotency_replay(self):
        """Record idempotent request replay."""
        if not self.enabled:
            return
        
        self.idempotency_replays_total.inc()
    
    def update_redis_status(self, is_up: bool):
        """Update Redis connectivity status."""
        if not self.enabled:
            return
        
        self.redis_up.set(1 if is_up else 0)
    
    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format."""
        if not self.enabled:
            return ""
        
        # Update dynamic metrics before export
        self._update_feature_flag_metrics()
        self._update_redis_status()
        
        return generate_latest(self.registry)
    
    def _update_redis_status(self):
        """Update Redis status by checking connectivity."""
        try:
            from src.services.rate_limit import get_rate_limiter
            rate_limiter = get_rate_limiter()
            
            # Try to ping Redis
            if hasattr(rate_limiter, 'redis_client') and rate_limiter.redis_client:
                rate_limiter.redis_client.ping()
                self.update_redis_status(True)
            else:
                self.update_redis_status(False)
        except Exception:
            self.update_redis_status(False)
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get health-related metrics for health endpoints."""
        if not self.enabled:
            return {
                'metrics_enabled': False
            }
        
        # Update Redis status
        self._update_redis_status()
        
        return {
            'metrics_enabled': True,
            'redis_up': bool(self.redis_up._value.get()),
            'total_requests': sum(
                sample.value for sample in self.http_requests_total.collect()[0].samples
            ) if hasattr(self, 'http_requests_total') else 0,
            'total_errors': sum(
                sample.value for sample in self.http_errors_total.collect()[0].samples
            ) if hasattr(self, 'http_errors_total') else 0,
            'rate_limit_hits': sum(
                sample.value for sample in self.rate_limit_hits_total.collect()[0].samples
            ) if hasattr(self, 'rate_limit_hits_total') else 0,
            'idempotency_replays': self.idempotency_replays_total._value.get() if hasattr(self, 'idempotency_replays_total') else 0
        }


# Global metrics service instance
_metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """Get global metrics service instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = MetricsService()
    return _metrics_service


def reset_metrics_service():
    """Reset global metrics service instance (for testing)."""
    global _metrics_service
    _metrics_service = None


class MetricsMiddleware:
    """Flask middleware for automatic metrics collection."""
    
    def __init__(self, app: Flask):
        self.app = app
        self.metrics_service = get_metrics_service()
        
        # Register before_request and after_request handlers
        app.before_request(self._before_request)
        app.after_request(self._after_request)
    
    def _before_request(self):
        """Record request start time."""
        g.request_start_time = time.time()
    
    def _after_request(self, response):
        """Record request metrics after processing."""
        if not hasattr(g, 'request_start_time'):
            return response
        
        # Calculate request duration
        duration = time.time() - g.request_start_time
        
        # Get route and method
        route = self._get_route_name()
        method = request.method
        status_code = response.status_code
        
        # Record metrics
        self.metrics_service.record_http_request(route, method, status_code, duration)
        
        return response
    
    def _get_route_name(self) -> str:
        """Get normalized route name for metrics."""
        if request.endpoint:
            # Use endpoint name for better grouping
            endpoint = request.endpoint
            
            # Map common endpoints to readable names
            endpoint_mapping = {
                'coordination_bp.coordination_endpoint': '/api/v1/coordination',
                'coordination_bp.health_check': '/api/v1/coordination/health',
                'coordination_bp.run': '/api/coordination/run',
                'auth_admin_bp.create_api_key': '/internal/keys/create',
                'auth_admin_bp.disable_api_key': '/internal/keys/disable',
                'auth_admin_bp.rotate_api_key': '/internal/keys/rotate',
                'inbound_bp.ping': '/api/inbound/_ping',
                'inbound_bp.order': '/api/inbound/order',
                'inbound_bp.status': '/api/inbound/status',
                'metrics_endpoint': '/metrics',
                'health_endpoint': '/healthz',
                'readiness_endpoint': '/readyz'
            }
            
            return endpoint_mapping.get(endpoint, endpoint)
        
        # Fallback to path with parameter normalization
        path = request.path
        
        # Normalize common path patterns
        import re
        
        # Replace UUIDs with placeholder
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{uuid}', path)
        
        # Replace other IDs with placeholder
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path


def create_metrics_blueprint():
    """Create Flask blueprint for metrics endpoints."""
    from flask import Blueprint
    
    metrics_bp = Blueprint('metrics', __name__)
    
    @metrics_bp.route('/metrics')
    def metrics_endpoint():
        """Prometheus metrics endpoint."""
        metrics_service = get_metrics_service()
        
        if not metrics_service.enabled:
            return "Metrics disabled", 404
        
        metrics_data = metrics_service.get_metrics()
        return Response(metrics_data, mimetype=CONTENT_TYPE_LATEST)
    
    @metrics_bp.route('/healthz')
    def health_endpoint():
        """Health check endpoint - always returns 200."""
        return {
            'status': 'healthy',
            'service': 'coordination-api',
            'timestamp': time.time()
        }
    
    @metrics_bp.route('/readyz')
    def readiness_endpoint():
        """Readiness check endpoint - checks dependencies."""
        metrics_service = get_metrics_service()
        health_metrics = metrics_service.get_health_metrics()
        
        # Check if critical dependencies are ready
        redis_up = health_metrics.get('redis_up', False)
        
        status = 'ready' if redis_up else 'not_ready'
        status_code = 200 if redis_up else 503
        
        response_data = {
            'status': status,
            'service': 'coordination-api',
            'timestamp': time.time(),
            'checks': {
                'redis': 'up' if redis_up else 'down',
                'metrics': 'enabled' if health_metrics.get('metrics_enabled') else 'disabled'
            },
            'metrics': health_metrics
        }
        
        return response_data, status_code
    
    return metrics_bp


def init_metrics(app: Flask):
    """Initialize metrics for Flask application."""
    # Initialize metrics middleware
    MetricsMiddleware(app)
    
    # Register metrics blueprint
    metrics_bp = create_metrics_blueprint()
    app.register_blueprint(metrics_bp)
    
    return get_metrics_service()


# Convenience functions for recording specific metrics
def record_http_request(route: str, method: str, status_code: int, duration: float):
    """Record HTTP request metrics."""
    get_metrics_service().record_http_request(route, method, status_code, duration)


def record_rate_limit_hit(scope: str):
    """Record rate limit hit."""
    get_metrics_service().record_rate_limit_hit(scope)


def record_idempotency_replay():
    """Record idempotency replay."""
    get_metrics_service().record_idempotency_replay()


def record_feature_flag(flag_name: str, enabled: bool):
    """Record feature flag status."""
    get_metrics_service().record_feature_flag(flag_name, enabled)


def record_redis_status(is_up: bool):
    """Record Redis status."""
    get_metrics_service().update_redis_status(is_up)


def update_redis_status(is_up: bool):
    """Update Redis status."""
    get_metrics_service().update_redis_status(is_up)



def record_http_request(route: str, method: str, status_code: int, duration: float):
    """Record HTTP request metrics."""
    get_metrics_service().record_http_request(route, method, status_code, duration)


def record_redis_status(is_up: bool):
    """Record Redis status."""
    get_metrics_service().update_redis_status(is_up)


def record_feature_flag(flag_name: str, enabled: bool):
    """Record feature flag usage."""
    # This is a placeholder - implement if needed
    pass

