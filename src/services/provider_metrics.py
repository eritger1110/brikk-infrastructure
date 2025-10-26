"""
Prometheus metrics for multi-provider orchestration.
Tracks provider requests, status, fallbacks, and latency.
"""

from prometheus_client import Counter, Histogram, Gauge

# Provider request counters
provider_requests_total = Counter(
    'brikk_relay_requests_total',
    'Total number of relay requests by provider',
    ['provider', 'status', 'fallback']
)

# Provider latency histogram
provider_latency_seconds = Histogram(
    'brikk_relay_latency_seconds',
    'Latency of relay requests in seconds',
    ['provider'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

# Provider availability gauge
provider_available = Gauge(
    'brikk_provider_available',
    'Provider availability (1=available, 0=unavailable)',
    ['provider']
)

def record_request(provider: str, status: str, fallback: bool, latency_ms: int):
    """
    Record a provider request with metrics.
    
    Args:
        provider: Provider name (openai, mistral)
        status: Request status (success, error)
        fallback: Whether fallback was used
        latency_ms: Request latency in milliseconds
    """
    provider_requests_total.labels(
        provider=provider,
        status=status,
        fallback=str(fallback).lower()
    ).inc()
    
    provider_latency_seconds.labels(provider=provider).observe(latency_ms / 1000.0)

def update_provider_availability(provider: str, available: bool):
    """
    Update provider availability gauge.
    
    Args:
        provider: Provider name (openai, mistral)
        available: Whether provider is available
    """
    provider_available.labels(provider=provider).set(1 if available else 0)

