# tests/test_billing_portal_stripe13.py
"""
Minimal deterministic tests for Stripe 13.x billing portal compatibility.
These tests validate request/validation/error handling without network calls.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from src.main import app as flask_app


@pytest.fixture(scope="function")
def client():
    """Fresh test client per test."""
    with flask_app.test_client() as c:
        yield c


def test_billing_portal_stripe13_error_handling(client, monkeypatch):
    """Test that Stripe 13.x error structure is handled correctly."""
    os.environ["STRIPE_SECRET_KEY"] = "sk_test_dummy"
    
    # Mock stripe module to simulate 13.x structure
    mock_stripe = MagicMock()
    
    # Create a mock StripeError that mimics Stripe 13.x structure
    class MockStripeError(Exception):
        def __init__(self, message, user_message=None):
            super().__init__(message)
            self.user_message = user_message
    
    mock_stripe.StripeError = MockStripeError
    mock_stripe.billing_portal.Session.create.side_effect = MockStripeError(
        "Test error", user_message="User-friendly error"
    )
    
    with patch('src.routes.app.stripe', mock_stripe):
        resp = client.post("/api/billing/portal", json={"customer_id": "cus_test"})
        
        assert resp.status_code == 502
        data = resp.get_json()
        assert "error" in data
        # Just check that it contains "Stripe error" - the exact message may vary
        assert "Stripe error" in data["error"]


def test_billing_portal_request_validation(client, monkeypatch):
    """Test request payload validation and processing."""
    os.environ["STRIPE_SECRET_KEY"] = "sk_test_dummy"
    
    # Mock successful Stripe session creation
    mock_stripe = MagicMock()
    mock_session = MagicMock()
    mock_session.url = "https://billing.stripe.com/session/test"
    mock_stripe.billing_portal.Session.create.return_value = mock_session
    
    with patch('src.routes.app.stripe', mock_stripe):
        # Test with valid customer_id
        resp = client.post("/api/billing/portal", json={"customer_id": "cus_valid"})
        
        assert resp.status_code == 200
        data = resp.get_json()
        assert "url" in data
        assert data["url"] == "https://billing.stripe.com/session/test"
        
        # Verify Stripe was called with correct parameters
        mock_stripe.billing_portal.Session.create.assert_called_with(
            customer="cus_valid",
            return_url="https://www.getbrikk.com/app/"
        )


def test_billing_portal_missing_stripe_key(client, monkeypatch):
    """Test error handling when STRIPE_SECRET_KEY is missing."""
    # Remove the environment variable
    os.environ.pop("STRIPE_SECRET_KEY", None)
    
    resp = client.post("/api/billing/portal", json={})
    
    assert resp.status_code == 500
    data = resp.get_json()
    assert "error" in data
    assert "missing" in data["error"].lower()
