"""
Test suite for health and readiness endpoints.

Tests health checks, dependency validation, and endpoint behavior.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from flask import Flask

from src.services.metrics import init_metrics


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
    with app.app_context():
        init_metrics(app)
    return app.test_client()


class TestHealthEndpoint:
    """Test /healthz endpoint functionality."""
    
    def test_health_endpoint_always_returns_200(self, client):
        """Test that health endpoint always returns 200."""
        response = client.get('/healthz')
        assert response.status_code == 200
    
    def test_health_endpoint_response_format(self, client):
        """Test health endpoint response format."""
        response = client.get('/healthz')
        data = response.get_json()
        
        # Check required fields
        assert 'status' in data
        assert 'service' in data
        assert 'timestamp' in data
        
        # Check values
        assert data['status'] == 'healthy'
        assert data['service'] == 'coordination-api'
        assert isinstance(data['timestamp'], (int, float))
        
        # Timestamp should be recent (within last 5 seconds)
        current_time = time.time()
        assert abs(current_time - data['timestamp']) < 5
    
    def test_health_endpoint_head_method(self, client):
        """Test health endpoint supports HEAD method."""
        response = client.head('/healthz')
        assert response.status_code == 200
        assert response.data == b''  # HEAD should have no body
    
    def test_health_endpoint_content_type(self, client):
        """Test health endpoint content type."""
        response = client.get('/healthz')
        assert response.content_type == 'application/json'


class TestReadinessEndpoint:
    """Test /readyz endpoint functionality."""
    
    @patch('redis.from_url')
    def test_readiness_endpoint_all_dependencies_healthy(self, mock_from_url, client):
        """Test readiness endpoint when all dependencies are healthy."""
        # Mock Redis connection success
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.return_value = True
        mock_from_url.return_value = mock_redis_instance
        
        response = client.get('/readyz')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'ready'
        assert data['service'] == 'coordination-api'
        assert 'timestamp' in data
        assert 'checks' in data
        assert data['checks']['redis'] is True
    
    @patch('redis.from_url')
    def test_readiness_endpoint_redis_unhealthy(self, mock_from_url, client):
        """Test readiness endpoint when Redis is unhealthy."""
        # Mock Redis connection failure
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.side_effect = Exception("Connection failed")
        mock_from_url.return_value = mock_redis_instance
        
        response = client.get('/readyz')
        assert response.status_code == 503
        
        data = response.get_json()
        assert data['status'] == 'not_ready'
        assert data['service'] == 'coordination-api'
        assert 'timestamp' in data
        assert 'checks' in data
        assert data['checks']['redis'] is False
    
    @patch('redis.from_url')
    def test_readiness_endpoint_redis_timeout(self, mock_from_url, client):
        """Test readiness endpoint when Redis times out."""
        # Mock Redis timeout
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.side_effect = TimeoutError("Redis timeout")
        mock_from_url.return_value = mock_redis_instance
        
        response = client.get('/readyz')
        assert response.status_code == 503
        
        data = response.get_json()
        assert data['status'] == 'not_ready'
        assert data['checks']['redis'] is False
    
    def test_readiness_endpoint_response_format(self, client):
        """Test readiness endpoint response format."""
        response = client.get('/readyz')
        data = response.get_json()
        
        # Check required fields
        assert 'status' in data
        assert 'service' in data
        assert 'timestamp' in data
        assert 'checks' in data
        
        # Check status values
        assert data['status'] in ['ready', 'not_ready']
        assert data['service'] == 'coordination-api'
        assert isinstance(data['timestamp'], (int, float))
        assert isinstance(data['checks'], dict)
        
        # Check that Redis check is present
        assert 'redis' in data['checks']
        assert isinstance(data['checks']['redis'], bool)
    
    def test_readiness_endpoint_head_method(self, client):
        """Test readiness endpoint supports HEAD method."""
        response = client.head('/readyz')
        # Status code depends on dependencies, but should be either 200 or 503
        assert response.status_code in [200, 503]
        assert response.data == b''  # HEAD should have no body
    
    def test_readiness_endpoint_content_type(self, client):
        """Test readiness endpoint content type."""
        response = client.get('/readyz')
        assert response.content_type == 'application/json'


class TestHealthVsReadiness:
    """Test differences between health and readiness endpoints."""
    
    @patch('redis.from_url')
    def test_health_vs_readiness_when_redis_down(self, mock_from_url, client):
        """Test that health is always OK but readiness fails when Redis is down."""
        # Mock Redis failure
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.side_effect = Exception("Redis down")
        mock_from_url.return_value = mock_redis_instance
        
        # Health should always be OK
        health_response = client.get('/healthz')
        assert health_response.status_code == 200
        health_data = health_response.get_json()
        assert health_data['status'] == 'healthy'
        
        # Readiness should fail
        readiness_response = client.get('/readyz')
        assert readiness_response.status_code == 503
        readiness_data = readiness_response.get_json()
        assert readiness_data['status'] == 'not_ready'
        assert readiness_data['checks']['redis'] is False
    
    def test_health_has_no_dependency_checks(self, client):
        """Test that health endpoint has no dependency checks."""
        response = client.get('/healthz')
        data = response.get_json()
        
        # Health should not have checks field
        assert 'checks' not in data
        
        # Should only have basic fields
        expected_fields = {'status', 'service', 'timestamp'}
        assert set(data.keys()) == expected_fields
    
    def test_readiness_has_dependency_checks(self, client):
        """Test that readiness endpoint has dependency checks."""
        response = client.get('/readyz')
        data = response.get_json()
        
        # Readiness should have checks field
        assert 'checks' in data
        assert isinstance(data['checks'], dict)
        
        # Should have at least Redis check
        assert 'redis' in data['checks']


class TestHealthEndpointIntegration:
    """Test health endpoints integration with Flask app."""
    
    def test_health_endpoints_registered(self, app):
        """Test that health endpoints are properly registered."""
        with app.app_context():
            init_metrics(app)
            
            # Check that routes are registered
            routes = [rule.rule for rule in app.url_map.iter_rules()]
            assert '/healthz' in routes
            assert '/readyz' in routes
    
    def test_health_endpoints_methods(self, app):
        """Test that health endpoints support correct HTTP methods."""
        with app.app_context():
            init_metrics(app)
            
            # Find health endpoint rules
            health_rule = None
            readiness_rule = None
            
            for rule in app.url_map.iter_rules():
                if rule.rule == '/healthz':
                    health_rule = rule
                elif rule.rule == '/readyz':
                    readiness_rule = rule
            
            assert health_rule is not None
            assert readiness_rule is not None
            
            # Check supported methods
            assert 'GET' in health_rule.methods
            assert 'HEAD' in health_rule.methods
            assert 'GET' in readiness_rule.methods
            assert 'HEAD' in readiness_rule.methods
    
    def test_health_endpoints_no_auth_required(self, client):
        """Test that health endpoints don't require authentication."""
        # Health endpoints should work without any authentication
        health_response = client.get('/healthz')
        assert health_response.status_code == 200
        
        readiness_response = client.get('/readyz')
        # Status depends on dependencies, but should not be 401/403
        assert readiness_response.status_code in [200, 503]


class TestHealthEndpointPerformance:
    """Test health endpoint performance characteristics."""
    
    def test_health_endpoint_fast_response(self, client):
        """Test that health endpoint responds quickly."""
        start_time = time.time()
        response = client.get('/healthz')
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Should respond in less than 100ms
        response_time = end_time - start_time
        assert response_time < 0.1
    
    @patch('redis.from_url')
    def test_readiness_endpoint_reasonable_response_time(self, mock_from_url, client):
        """Test that readiness endpoint responds in reasonable time."""
        # Mock Redis with small delay
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.return_value = True
        mock_from_url.return_value = mock_redis_instance
        
        start_time = time.time()
        response = client.get('/readyz')
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Should respond in less than 1 second even with dependency checks
        response_time = end_time - start_time
        assert response_time < 1.0
    
    def test_health_endpoints_concurrent_requests(self, client):
        """Test that health endpoints handle concurrent requests."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            try:
                response = client.get('/healthz')
                results.put(response.status_code)
            except Exception as e:
                results.put(str(e))
        
        # Start multiple concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that all requests succeeded
        status_codes = []
        while not results.empty():
            status_codes.append(results.get())
        
        assert len(status_codes) == 10
        assert all(code == 200 for code in status_codes)


class TestHealthEndpointErrorHandling:
    """Test health endpoint error handling."""
    
    @patch('redis.from_url')
    def test_readiness_handles_redis_import_error(self, mock_from_url, client):
        """Test readiness endpoint handles Redis import errors gracefully."""
        # Mock Redis import failure
        mock_from_url.side_effect = ImportError("Redis not available")
        
        response = client.get('/readyz')
        assert response.status_code == 503
        
        data = response.get_json()
        assert data['status'] == 'not_ready'
        assert data['checks']['redis'] is False
    
    @patch('redis.from_url')
    def test_readiness_handles_unexpected_redis_errors(self, mock_from_url, client):
        """Test readiness endpoint handles unexpected Redis errors."""
        # Mock unexpected Redis error
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping.side_effect = RuntimeError("Unexpected error")
        mock_from_url.return_value = mock_redis_instance
        
        response = client.get('/readyz')
        assert response.status_code == 503
        
        data = response.get_json()
        assert data['status'] == 'not_ready'
        assert data['checks']['redis'] is False
    
    def test_health_endpoint_always_works(self, client):
        """Test that health endpoint works even if other systems fail."""
        # Health should always work regardless of other system states
        response = client.get('/healthz')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'healthy'


if __name__ == '__main__':
    pytest.main([__file__])

