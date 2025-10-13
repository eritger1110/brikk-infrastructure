"""
Test suite for Prometheus metrics functionality.

Tests metrics collection, labels, health endpoints, and feature flag behavior.
"""

import pytest
import os
import time
from unittest.mock import patch, MagicMock
from flask import Flask
from prometheus_client import REGISTRY, CollectorRegistry

from src.services.metrics import (
    MetricsService, get_metrics_service, init_metrics,
)


@pytest.fixture
def app():
    """Create test Flask app."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["BRIKK_METRICS_ENABLED"] = "true"
    with app.app_context():
        init_metrics(app)
        yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestMetricsService:
    """Test MetricsService functionality."""

    def test_metrics_service_initialization(self, app):
        """Test metrics service initializes correctly."""
        with app.app_context():
            service = get_metrics_service()
            assert service.enabled is True
            assert service.registry is not None

            # Check that all metrics are initialized
            assert hasattr(service, "http_requests_total")
            assert hasattr(service, "http_request_duration_seconds")
            assert hasattr(service, "http_errors_total")
            assert hasattr(service, "rate_limit_hits_total")
            assert hasattr(service, "idempotency_replays_total")
            assert hasattr(service, "redis_up")
            assert hasattr(service, "feature_flags")

    def test_metrics_disabled(self):
        """Test metrics service when disabled."""
        with patch.dict(os.environ, {"BRIKK_METRICS_ENABLED": "false"}):
            app = Flask(__name__)
            with app.app_context():
                init_metrics(app)
                service = get_metrics_service()
                assert service.enabled is False


class TestMetricsIntegration:
    """Test metrics integration with Flask app."""

    def test_metrics_endpoint_enabled(self, client):
        """Test /metrics endpoint when enabled."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.content_type == "text/plain; version=0.0.4; charset=utf-8"

        # Check for expected metrics
        data = response.get_data(as_text=True)
        assert "brikk_http_requests_total" in data

    def test_metrics_endpoint_disabled(self):
        """Test /metrics endpoint when disabled."""
        with patch.dict(os.environ, {"BRIKK_METRICS_ENABLED": "false"}):
            app = Flask(__name__)
            with app.app_context():
                init_metrics(app)
                client = app.test_client()

                response = client.get("/metrics")
                assert response.status_code == 404

class TestMetricsMiddleware:
    """Test metrics middleware functionality."""

    def test_metrics_middleware_records_requests(self, app, client):
        """Test that metrics middleware records HTTP requests."""
        # Add a test route
        @app.route("/test")
        def test_route():
            return {"message": "test"}

        # Make a request
        response = client.get("/test")
        assert response.status_code == 200

        # Check metrics
        with app.app_context():
            service = get_metrics_service()
            metrics_data = service.get_metrics()

            # Should record the request
            assert "brikk_http_requests_total" in metrics_data
            assert "route=\"/test\"" in metrics_data
            assert "method=\"GET\"" in metrics_data
            assert "status=\"200\"" in metrics_data

