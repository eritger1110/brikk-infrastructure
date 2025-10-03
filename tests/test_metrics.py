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
    record_http_request, record_rate_limit_hit, record_idempotency_replay,
    record_redis_status, record_feature_flag
)


@pytest.fixture
def app():
    """Create test Flask app."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['BRIKK_METRICS_ENABLED'] = 'true'
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def metrics_service():
    """Create fresh metrics service for testing."""
    # Use a separate registry for testing to avoid conflicts
    test_registry = CollectorRegistry()
    service = MetricsService(enabled=True, registry=test_registry)
    return service


class TestMetricsService:
    """Test MetricsService functionality."""
    
    def test_metrics_service_initialization(self, metrics_service):
        """Test metrics service initializes correctly."""
        assert metrics_service.enabled is True
        assert metrics_service.registry is not None
        
        # Check that all metrics are initialized
        assert hasattr(metrics_service, 'http_requests_total')
        assert hasattr(metrics_service, 'http_request_duration_seconds')
        assert hasattr(metrics_service, 'http_errors_total')
        assert hasattr(metrics_service, 'rate_limit_hits_total')
        assert hasattr(metrics_service, 'idempotency_replays_total')
        assert hasattr(metrics_service, 'redis_up')
        assert hasattr(metrics_service, 'feature_flags')
    
    def test_metrics_disabled(self):
        """Test metrics service when disabled."""
        service = MetricsService(enabled=False)
        assert service.enabled is False
        
        # Should not create metrics when disabled
        assert service.http_requests_total is None
        assert service.http_request_duration_seconds is None
    
    def test_record_http_request(self, metrics_service):
        """Test HTTP request recording."""
        # Record a request
        metrics_service.record_http_request(
            route='/api/v1/coordination',
            method='POST',
            status_code=200,
            duration_seconds=0.5
        )
        
        # Get metrics data
        metrics_data = metrics_service.get_metrics()
        
        # Check that metrics were recorded
        assert 'brikk_http_requests_total' in metrics_data
        assert 'brikk_http_request_duration_seconds' in metrics_data
        
        # Check labels
        assert 'route="/api/v1/coordination"' in metrics_data
        assert 'method="POST"' in metrics_data
        assert 'status="200"' in metrics_data
    
    def test_record_http_error(self, metrics_service):
        """Test HTTP error recording."""
        metrics_service.record_http_error(
            route='/api/v1/coordination',
            error_kind='validation_error'
        )
        
        metrics_data = metrics_service.get_metrics()
        assert 'brikk_http_errors_total' in metrics_data
        assert 'route="/api/v1/coordination"' in metrics_data
        assert 'kind="validation_error"' in metrics_data
    
    def test_record_rate_limit_hit(self, metrics_service):
        """Test rate limit hit recording."""
        metrics_service.record_rate_limit_hit(scope='org:test-org')
        
        metrics_data = metrics_service.get_metrics()
        assert 'brikk_rate_limit_hits_total' in metrics_data
        assert 'scope="org:test-org"' in metrics_data
    
    def test_record_idempotency_replay(self, metrics_service):
        """Test idempotency replay recording."""
        metrics_service.record_idempotency_replay()
        
        metrics_data = metrics_service.get_metrics()
        assert 'brikk_idempotency_replays_total' in metrics_data
    
    def test_record_redis_status(self, metrics_service):
        """Test Redis status recording."""
        # Test Redis up
        metrics_service.record_redis_status(True)
        metrics_data = metrics_service.get_metrics()
        assert 'brikk_redis_up 1.0' in metrics_data
        
        # Test Redis down
        metrics_service.record_redis_status(False)
        metrics_data = metrics_service.get_metrics()
        assert 'brikk_redis_up 0.0' in metrics_data
    
    def test_record_feature_flag(self, metrics_service):
        """Test feature flag recording."""
        metrics_service.record_feature_flag('BRIKK_FEATURE_PER_ORG_KEYS', True)
        
        metrics_data = metrics_service.get_metrics()
        assert 'brikk_feature_flag' in metrics_data
        assert 'flag="BRIKK_FEATURE_PER_ORG_KEYS"' in metrics_data
        assert 'enabled="true"' in metrics_data
    
    def test_normalize_route(self, metrics_service):
        """Test route normalization."""
        # Test known endpoints
        assert metrics_service._normalize_route('/api/v1/coordination') == '/api/v1/coordination'
        assert metrics_service._normalize_route('/metrics') == '/metrics'
        assert metrics_service._normalize_route('/healthz') == '/healthz'
        assert metrics_service._normalize_route('/readyz') == '/readyz'
        
        # Test UUID replacement
        uuid_route = '/api/agents/123e4567-e89b-12d3-a456-426614174000'
        assert metrics_service._normalize_route(uuid_route) == '/api/agents/{uuid}'
        
        # Test ID replacement
        id_route = '/api/orders/12345'
        assert metrics_service._normalize_route(id_route) == '/api/orders/{id}'


class TestMetricsIntegration:
    """Test metrics integration with Flask app."""
    
    def test_init_metrics(self, app):
        """Test metrics initialization with Flask app."""
        with app.app_context():
            init_metrics(app)
            
            # Check that metrics service is available
            service = get_metrics_service()
            assert service is not None
            assert service.enabled is True
    
    def test_metrics_endpoint_enabled(self, app):
        """Test /metrics endpoint when enabled."""
        with app.app_context():
            init_metrics(app)
            client = app.test_client()
            
            response = client.get('/metrics')
            assert response.status_code == 200
            assert response.content_type == 'text/plain; version=0.0.4; charset=utf-8'
            
            # Check for expected metrics
            data = response.get_data(as_text=True)
            assert 'brikk_http_requests_total' in data
            assert 'brikk_redis_up' in data
    
    def test_metrics_endpoint_disabled(self, app):
        """Test /metrics endpoint when disabled."""
        app.config['BRIKK_METRICS_ENABLED'] = 'false'
        
        with app.app_context():
            init_metrics(app)
            client = app.test_client()
            
            response = client.get('/metrics')
            assert response.status_code == 404
            assert b'Metrics disabled' in response.data
    
    def test_health_endpoint(self, app):
        """Test /healthz endpoint."""
        with app.app_context():
            init_metrics(app)
            client = app.test_client()
            
            response = client.get('/healthz')
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['status'] == 'healthy'
            assert data['service'] == 'coordination-api'
            assert 'timestamp' in data
    
    @patch('src.services.metrics.redis.Redis')
    def test_readiness_endpoint_redis_up(self, mock_redis, app):
        """Test /readyz endpoint when Redis is available."""
        # Mock Redis connection
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.return_value = True
        mock_redis.return_value = mock_redis_instance
        
        with app.app_context():
            init_metrics(app)
            client = app.test_client()
            
            response = client.get('/readyz')
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['status'] == 'ready'
            assert data['checks']['redis'] is True
    
    @patch('src.services.metrics.redis.Redis')
    def test_readiness_endpoint_redis_down(self, mock_redis, app):
        """Test /readyz endpoint when Redis is unavailable."""
        # Mock Redis connection failure
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.side_effect = Exception("Connection failed")
        mock_redis.return_value = mock_redis_instance
        
        with app.app_context():
            init_metrics(app)
            client = app.test_client()
            
            response = client.get('/readyz')
            assert response.status_code == 503
            
            data = response.get_json()
            assert data['status'] == 'not_ready'
            assert data['checks']['redis'] is False


class TestMetricsMiddleware:
    """Test metrics middleware functionality."""
    
    def test_metrics_middleware_records_requests(self, app):
        """Test that metrics middleware records HTTP requests."""
        with app.app_context():
            init_metrics(app)
            
            # Add a test route
            @app.route('/test')
            def test_route():
                return {'message': 'test'}
            
            client = app.test_client()
            
            # Make a request
            response = client.get('/test')
            assert response.status_code == 200
            
            # Check metrics
            service = get_metrics_service()
            metrics_data = service.get_metrics()
            
            # Should record the request
            assert 'brikk_http_requests_total' in metrics_data
            assert 'route="/test"' in metrics_data
            assert 'method="GET"' in metrics_data
            assert 'status="200"' in metrics_data
    
    def test_metrics_middleware_records_duration(self, app):
        """Test that metrics middleware records request duration."""
        with app.app_context():
            init_metrics(app)
            
            # Add a slow test route
            @app.route('/slow')
            def slow_route():
                time.sleep(0.1)  # 100ms delay
                return {'message': 'slow'}
            
            client = app.test_client()
            
            # Make a request
            response = client.get('/slow')
            assert response.status_code == 200
            
            # Check metrics
            service = get_metrics_service()
            metrics_data = service.get_metrics()
            
            # Should record duration
            assert 'brikk_http_request_duration_seconds' in metrics_data
            assert 'route="/slow"' in metrics_data


class TestGlobalMetricsFunctions:
    """Test global metrics recording functions."""
    
    @patch('src.services.metrics.get_metrics_service')
    def test_record_http_request_function(self, mock_get_service):
        """Test global record_http_request function."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        record_http_request('/api/test', 'POST', 201, 0.5)
        
        mock_service.record_http_request.assert_called_once_with(
            route='/api/test',
            method='POST', 
            status_code=201,
            duration_seconds=0.5
        )
    
    @patch('src.services.metrics.get_metrics_service')
    def test_record_rate_limit_hit_function(self, mock_get_service):
        """Test global record_rate_limit_hit function."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        record_rate_limit_hit('org:test')
        
        mock_service.record_rate_limit_hit.assert_called_once_with('org:test')
    
    @patch('src.services.metrics.get_metrics_service')
    def test_record_idempotency_replay_function(self, mock_get_service):
        """Test global record_idempotency_replay function."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        record_idempotency_replay()
        
        mock_service.record_idempotency_replay.assert_called_once()
    
    @patch('src.services.metrics.get_metrics_service')
    def test_record_redis_status_function(self, mock_get_service):
        """Test global record_redis_status function."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        record_redis_status(True)
        
        mock_service.record_redis_status.assert_called_once_with(True)
    
    @patch('src.services.metrics.get_metrics_service')
    def test_record_feature_flag_function(self, mock_get_service):
        """Test global record_feature_flag function."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        record_feature_flag('TEST_FLAG', False)
        
        mock_service.record_feature_flag.assert_called_once_with('TEST_FLAG', False)


class TestMetricsLabels:
    """Test metrics labels and normalization."""
    
    def test_route_normalization_patterns(self, metrics_service):
        """Test various route normalization patterns."""
        test_cases = [
            # (input_route, expected_output)
            ('/api/v1/coordination', '/api/v1/coordination'),
            ('/api/agents/123e4567-e89b-12d3-a456-426614174000', '/api/agents/{uuid}'),
            ('/api/orders/12345', '/api/orders/{id}'),
            ('/api/users/999/profile', '/api/users/{id}/profile'),
            ('/metrics', '/metrics'),
            ('/healthz', '/healthz'),
            ('/readyz', '/readyz'),
            ('/api/unknown/path', '/api/unknown/path'),
        ]
        
        for input_route, expected in test_cases:
            result = metrics_service._normalize_route(input_route)
            assert result == expected, f"Route {input_route} should normalize to {expected}, got {result}"
    
    def test_metrics_labels_consistency(self, metrics_service):
        """Test that metrics labels are consistent across different calls."""
        route = '/api/v1/coordination'
        method = 'POST'
        
        # Record multiple requests
        for status in [200, 400, 500]:
            metrics_service.record_http_request(route, method, status, 0.1)
        
        metrics_data = metrics_service.get_metrics()
        
        # All should use the same route and method labels
        assert metrics_data.count(f'route="{route}"') >= 3
        assert metrics_data.count(f'method="{method}"') >= 3
        
        # Different status codes should be recorded
        assert 'status="200"' in metrics_data
        assert 'status="400"' in metrics_data
        assert 'status="500"' in metrics_data


class TestMetricsConfiguration:
    """Test metrics configuration and environment variables."""
    
    def test_metrics_enabled_by_default(self):
        """Test that metrics are enabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            service = MetricsService()
            assert service.enabled is True
    
    def test_metrics_disabled_by_env(self):
        """Test that metrics can be disabled via environment variable."""
        with patch.dict(os.environ, {'BRIKK_METRICS_ENABLED': 'false'}):
            service = MetricsService()
            assert service.enabled is False
    
    def test_metrics_enabled_by_env(self):
        """Test that metrics can be explicitly enabled via environment variable."""
        with patch.dict(os.environ, {'BRIKK_METRICS_ENABLED': 'true'}):
            service = MetricsService()
            assert service.enabled is True
    
    def test_invalid_env_value_defaults_to_enabled(self):
        """Test that invalid environment values default to enabled."""
        with patch.dict(os.environ, {'BRIKK_METRICS_ENABLED': 'invalid'}):
            service = MetricsService()
            assert service.enabled is True


if __name__ == '__main__':
    pytest.main([__file__])
