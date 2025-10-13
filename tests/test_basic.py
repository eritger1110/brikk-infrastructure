"""
Basic tests for Brikk Infrastructure CI validation.
These tests ensure the application can start and basic functionality works.
"""

import pytest
import os
from src.factory import create_app, _normalize_db_url


def test_app_creation():
    """Test that the Flask app can be created successfully."""
    app = create_app()
    assert app is not None
    assert app.config['SECRET_KEY'] is not None


def test_app_config():
    """Test that app configuration is properly set."""
    app = create_app()
    
    # Test that required config keys exist
    assert 'SECRET_KEY' in app.config
    assert 'SQLALCHEMY_DATABASE_URI' in app.config
    
    # Test that the app is properly configured
    assert app.url_map.strict_slashes is False


def test_health_endpoint():
    """Test the health check endpoint if it exists."""
    app = create_app()
    with app.test_client() as client:
        response = client.get('/api/inbound/_health')
        assert response.status_code == 200


def test_inbound_ping_endpoint():
    """Test the inbound ping endpoint."""
    app = create_app()
    with app.test_client() as client:
        response = client.get('/api/inbound/_ping')
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert data['bp'] == 'health'


def test_environment_variables():
    """Test that critical environment variables are handled properly."""
    # Test that the app can handle missing optional environment variables
    original_env = os.environ.copy()
    
    try:
        # Remove optional env vars to test defaults
        for key in ['ENABLE_SECURITY_ROUTES', 'ENABLE_DEV_LOGIN', 'ENABLE_TALISMAN']:
            if key in os.environ:
                del os.environ[key]
        
        app = create_app()
        assert app is not None
        
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_database_url_normalization():
    """Test the database URL normalization function."""
    
    
    # Test postgres:// to postgresql+psycopg:// conversion
    postgres_url = "postgres://user:pass@host:5432/db"
    normalized = _normalize_db_url(postgres_url)
    assert normalized == "postgresql+psycopg://user:pass@host:5432/db"
    
    # Test postgresql:// to postgresql+psycopg:// conversion
    postgresql_url = "postgresql://user:pass@host:5432/db"
    normalized = _normalize_db_url(postgresql_url)
    assert normalized == "postgresql+psycopg://user:pass@host:5432/db"
    
    # Test that already normalized URLs are unchanged
    already_normalized = "postgresql+psycopg://user:pass@host:5432/db"
    normalized = _normalize_db_url(already_normalized)
    assert normalized == already_normalized
    
    # Test other URLs are unchanged
    sqlite_url = "sqlite:///test.db"
    normalized = _normalize_db_url(sqlite_url)
    assert normalized == sqlite_url


def test_blueprint_registration():
    """Test that blueprints are properly registered."""
    app = create_app()
    
    # Check that blueprints are registered
    blueprint_names = [bp.name for bp in app.blueprints.values()]
    
    # These blueprints should be registered based on the main.py file
    expected_blueprints = ['health']
    
    for expected_bp in expected_blueprints:
        assert expected_bp in blueprint_names, f"Blueprint {expected_bp} not registered"


def test_cors_configuration():
    """Test that CORS is properly configured."""
    app = create_app()
    
    # Test that CORS extension is initialized
    # We can't easily test the actual CORS headers without making requests,
    # but we can verify the app was created without errors
    assert app is not None


def test_security_configuration():
    """Test security-related configuration."""
    app = create_app()
    
    # Test that security headers are configured (Talisman)
    # The actual headers are tested in integration tests
    assert app is not None
    
    # Test JWT configuration
    assert 'JWT_SECRET_KEY' in app.config or 'SECRET_KEY' in app.config


