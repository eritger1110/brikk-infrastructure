"""
Pytest configuration for Brikk infrastructure tests.
"""
import pytest
import os
import tempfile
from unittest.mock import patch

# Set test environment variables
os.environ['FLASK_ENV'] = 'testing'
os.environ['TESTING'] = 'true'
os.environ['BRIKK_ENCRYPTION_KEY'] = 'test_key_32_bytes_long_for_fernet'


@pytest.fixture(scope='session')
def test_encryption_key():
    """Provide test encryption key for all tests."""
    return 'test_key_32_bytes_long_for_fernet'


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    db_fd, db_path = tempfile.mkstemp()
    yield f'sqlite:///{db_path}'
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def mock_redis():
    """Mock Redis for testing."""
    from unittest.mock import MagicMock
    mock_redis = MagicMock()
    
    # Mock common Redis operations
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.scan_iter.return_value = []
    mock_redis.info.return_value = {
        'used_memory': 1024000,
        'connected_clients': 1
    }
    mock_redis.eval.return_value = 0
    
    return mock_redis


@pytest.fixture
def feature_flags():
    """Provide common feature flag configurations for testing."""
    return {
        'enabled': {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'true',
            'BRIKK_IDEM_ENABLED': 'true',
            'BRIKK_ALLOW_UUID4': 'false'
        },
        'disabled': {
            'BRIKK_FEATURE_PER_ORG_KEYS': 'false',
            'BRIKK_IDEM_ENABLED': 'false',
            'BRIKK_ALLOW_UUID4': 'true'
        }
    }


@pytest.fixture
def sample_envelope_data():
    """Provide sample envelope data for testing."""
    from datetime import datetime, timezone
    
    return {
        "version": "1.0",
        "message_id": "01234567-89ab-cdef-0123-456789abcdef",
        "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "type": "message",
        "sender": {"agent_id": "test-sender"},
        "recipient": {"agent_id": "test-recipient"},
        "payload": {"action": "test", "data": "sample"}
    }


@pytest.fixture
def admin_token():
    """Provide admin token for testing."""
    return 'test_admin_token_for_testing'


# Configure pytest to handle async tests if needed
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring external services"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "redis: mark test as requiring Redis connection"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Mark integration tests
        if "integration" in item.name.lower() or "test_integration" in item.name:
            item.add_marker(pytest.mark.integration)
        
        # Mark Redis tests
        if "redis" in item.name.lower() or "idempotency" in item.name.lower():
            item.add_marker(pytest.mark.redis)
        
        # Mark slow tests
        if "rotation" in item.name.lower() or "full_flow" in item.name.lower():
            item.add_marker(pytest.mark.slow)
