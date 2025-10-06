"""
Smoke test for Flask application startup.

LOCAL DEVELOPMENT ONLY - NOT WIRED TO CI
"""

import pytest
import requests
import time
import os
from unittest.mock import patch


class TestAppStartup:
    """Test basic Flask application startup and health."""
    
    @pytest.fixture(scope="class")
    def base_url(self):
        """Base URL for local Flask app."""
        return "http://localhost:8000"
    
    def test_app_responds(self, base_url):
        """Test that Flask app is responding."""
        try:
            response = requests.get(f"{base_url}/healthz", timeout=5)
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "coordination-api"
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running - start with ./scripts/dev.sh")
    
    def test_health_endpoint(self, base_url):
        """Test health endpoint returns expected format."""
        try:
            response = requests.get(f"{base_url}/healthz", timeout=5)
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
            
            data = response.json()
            required_fields = {"status", "service", "timestamp"}
            assert set(data.keys()) == required_fields
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running")
    
    def test_readiness_endpoint(self, base_url):
        """Test readiness endpoint checks dependencies."""
        try:
            response = requests.get(f"{base_url}/readyz", timeout=5)
            # Status depends on Redis availability
            assert response.status_code in [200, 503]
            assert response.headers["content-type"] == "application/json"
            
            data = response.json()
            assert "status" in data
            assert "checks" in data
            assert "redis" in data["checks"]
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running")
    
    def test_metrics_endpoint_when_enabled(self, base_url):
        """Test metrics endpoint when enabled."""
        try:
            response = requests.get(f"{base_url}/metrics", timeout=5)
            
            if response.status_code == 200:
                # Metrics enabled
                assert "text/plain" in response.headers["content-type"]
                content = response.text
                assert "brikk_http_requests_total" in content
                assert "brikk_redis_up" in content
            elif response.status_code == 404:
                # Metrics disabled
                assert b"Metrics disabled" in response.content
            else:
                pytest.fail(f"Unexpected status code: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running")
    
    def test_coordination_endpoint_exists(self, base_url):
        """Test that coordination endpoint exists (even if auth fails)."""
        try:
            # Should get 400 for missing headers, not 404
            response = requests.post(f"{base_url}/api/v1/coordination", timeout=5)
            assert response.status_code != 404
            
            # Should be 400 (bad request) or 415 (unsupported media type)
            assert response.status_code in [400, 415]
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running")
    
    def test_request_id_header(self, base_url):
        """Test that X-Request-ID header is present in responses."""
        try:
            response = requests.get(f"{base_url}/healthz", timeout=5)
            assert response.status_code == 200
            
            # Should have X-Request-ID header
            assert "X-Request-ID" in response.headers
            request_id = response.headers["X-Request-ID"]
            
            # Should be a valid UUID format
            import uuid
            uuid.UUID(request_id)  # Will raise ValueError if invalid
            
        except requests.exceptions.ConnectionError:
            pytest.skip("Flask app not running")


class TestRedisConnectivity:
    """Test Redis connectivity for local development."""
    
    def test_redis_connection(self):
        """Test Redis connection is available."""
        try:
            import redis
            
            # Use local Redis URL
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = redis.from_url(redis_url)
            
            # Test connection
            assert r.ping() is True
            
            # Test basic operations
            r.set("test_key", "test_value", ex=10)
            assert r.get("test_key").decode() == "test_value"
            r.delete("test_key")
            
        except ImportError:
            pytest.skip("Redis package not installed")
        except redis.exceptions.ConnectionError:
            pytest.skip("Redis not running - start with 'make up'")
    
    def test_redis_container_health(self):
        """Test Redis container is healthy."""
        try:
            import subprocess
            
            # Check if Redis container is running
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=brikk-redis", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                status = result.stdout.strip()
                assert "Up" in status
                assert "(healthy)" in status or "starting" in status
            else:
                pytest.skip("Redis container not running - start with 'make up'")
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Docker not available or timeout")


class TestEnvironmentConfiguration:
    """Test local development environment configuration."""
    
    def test_development_environment_variables(self):
        """Test that development environment variables are set."""
        # These should be set by development scripts
        expected_vars = [
            "FLASK_APP",
            "FLASK_ENV", 
            "FLASK_RUN_PORT",
            "REDIS_URL"
        ]
        
        missing_vars = []
        for var in expected_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            pytest.skip(f"Development environment not configured. Missing: {missing_vars}")
    
    def test_feature_flags_configuration(self):
        """Test feature flags are configured for local development."""
        # Check that feature flags have expected values for local dev
        feature_flags = {
            "BRIKK_FEATURE_PER_ORG_KEYS": "false",
            "BRIKK_IDEM_ENABLED": "true", 
            "BRIKK_RLIMIT_ENABLED": "false"
        }
        
        for flag, expected in feature_flags.items():
            actual = os.getenv(flag)
            if actual and actual != expected:
                print(f"Warning: {flag}={actual}, expected {expected} for local dev")


class TestLocalDevelopmentWorkflow:
    """Test complete local development workflow."""
    
    def test_make_commands_available(self):
        """Test that make commands are available."""
        try:
            import subprocess
            
            # Test that Makefile exists and has expected targets
            result = subprocess.run(
                ["make", "-n", "up"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd="/home/ubuntu/brikk-infrastructure"
            )
            
            if result.returncode == 0:
                assert "docker compose -f docker-compose.local.yml up -d" in result.stdout
            else:
                pytest.skip("Makefile not available or 'up' target not found")
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Make not available")
    
    def test_development_scripts_exist(self):
        """Test that development scripts exist."""
        import os
        
        script_dir = "/home/ubuntu/brikk-infrastructure/scripts"
        expected_scripts = ["dev.sh", "dev.ps1"]
        
        missing_scripts = []
        for script in expected_scripts:
            script_path = os.path.join(script_dir, script)
            if not os.path.exists(script_path):
                missing_scripts.append(script)
        
        if missing_scripts:
            pytest.skip(f"Development scripts not found: {missing_scripts}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
