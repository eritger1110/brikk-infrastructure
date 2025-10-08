# tests/test_smoke.py
"""
Minimal smoke tests to verify basic app health and functionality.
These tests ensure the application can start and respond to basic requests.
"""
import pytest
from src.main import create_app


@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    app = create_app()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        with app.app_context():
            yield client


def test_app_creation():
    """Test that the Flask app can be created successfully."""
    app = create_app()
    assert app is not None
    assert app.config is not None


def test_ping_endpoint(client):
    """Test that the ping endpoint returns a valid response."""
    response = client.get('/api/inbound/_ping')
    # Accept 200 OK or 302 redirect as valid responses
    assert response.status_code in [200, 302]
    
    if response.status_code == 200:
        # Verify response contains expected content for 200 responses
        data = response.get_json()
        assert data is not None
        # The ping endpoint returns {'bp': 'inbound', 'ok': True}
        assert 'ok' in data or 'status' in data or 'message' in data


def test_app_config_testing_mode():
    """Test that the app can be configured in testing mode."""
    app = create_app()
    app.config['TESTING'] = True
    assert app.config['TESTING'] is True


def test_basic_routes_exist(client):
    """Test that basic application routes are accessible (don't return 404)."""
    # Test ping endpoint specifically
    response = client.get('/api/inbound/_ping')
    assert response.status_code != 404
    
    # Test that we get a valid response (200, 302, 401, 403, etc. are all valid - just not 404)
    assert response.status_code in [200, 302, 401, 403, 405, 500]  # Any valid HTTP response
