'''
Pytest configuration for Brikk infrastructure tests.
'''
import pytest
import os

# Set test environment variables
os.environ["FLASK_ENV"] = "testing"
os.environ["TESTING"] = "true"
os.environ["BRIKK_ENCRYPTION_KEY"] = "test_key_32_bytes_long_for_fernet"

from src.models import agent, ai_coordination, api_key, audit_log, customer_profile, discovery, economy, message_log, org, purchase, user, webhook, workflow, workflow_execution, workflow_step

@pytest.fixture(scope='function')
def app():
    from src.factory import create_app
    from src.database import db

    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret-key"
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    return app.test_client()

