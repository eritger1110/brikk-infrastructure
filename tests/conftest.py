import pytest
import os
import tempfile
from unittest.mock import patch

# Set test environment variables
os.environ["FLASK_ENV"] = "testing"
os.environ["TESTING"] = "true"
os.environ["BRIKK_ENCRYPTION_KEY"] = "test_key_32_bytes_long_for_fernet"

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    db_fd, db_path = tempfile.mkstemp()
    with patch.dict(os.environ, {
        "DATABASE_URL": f"sqlite:///{db_path}",
    }):
        from src.factory import create_app
        from src.database import db
        app = create_app()
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()




import pytest
from prometheus_client import REGISTRY

@pytest.fixture(autouse=True)
def clear_prometheus_registry():
    """Clear the default prometheus registry before each test."""
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)
    yield

