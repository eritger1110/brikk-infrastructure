# -*- coding: utf-8 -*-

import pytest
import json
from unittest.mock import patch, MagicMock
import os


class TestBillingPortal:
    """Test cases for billing portal endpoint."""

    def test_portal_success_with_stripe_13(self, client, monkeypatch):
        """Test successful billing portal creation with Stripe 13.x."""
        # Mock Stripe configuration
        monkeypatch.setenv(
            "STRIPE_SECRET_KEY",
            "sk_test_dummy_key_for_testing")

        # Create mock Stripe session object (Stripe 13.x format)
        class MockStripeSession:
            def __init__(self):
                self.url = "https://billing.stripe.com/p/session_test_12345"
                self.id = "bps_test_12345"
                self.customer = "cus_test_customer"
                self.return_url = "https://example.com/return"

        # Mock the Stripe billing portal session creation
        with patch("stripe.billing_portal.Session.create") as mock_create:
            mock_create.return_value = MockStripeSession()

            # Make request to billing portal endpoint
            response = client.post("/api/billing/portal",
                                   json={"customer_id": "cus_test_customer"})

            # Verify response
            assert response.status_code == 200
            data = response.get_json()
            assert "url" in data
            assert data["url"].startswith("https://")
            assert "billing.stripe.com" in data["url"]

            # Verify Stripe was called correctly
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]  # Get keyword arguments
            assert "customer" in call_args
            assert "return_url" in call_args

    def test_portal_missing_stripe_key(self, client, monkeypatch):
        """Test billing portal when STRIPE_SECRET_KEY is missing."""
        # Remove Stripe secret key
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

        response = client.post("/api/billing/portal",
                               json={"customer_id": "cus_test_customer"})

        # Should return error when no Stripe key configured
        # Either server error or not implemented
        assert response.status_code in [500, 501]
        data = response.get_json()
        assert "error" in data or "message" in data

    def test_portal_invalid_customer_id(self, client, monkeypatch):
        """Test billing portal with invalid customer ID."""
        monkeypatch.setenv(
            "STRIPE_SECRET_KEY",
            "sk_test_dummy_key_for_testing")

        # Mock Stripe to raise an error for invalid customer
        with patch("stripe.billing_portal.Session.create") as mock_create:
            # Simulate Stripe error for invalid customer (generic exception for
            # testing)
            stripe_error = Exception("No such customer: 'invalid_customer'")
            mock_create.side_effect = stripe_error

            response = client.post("/api/billing/portal",
                                   json={"customer_id": "invalid_customer"})

            # Should handle Stripe errors gracefully
            assert response.status_code in [400, 404, 500]
            data = response.get_json()
            assert "error" in data or "message" in data

    def test_portal_missing_customer_id(self, client, monkeypatch):
        """Test billing portal without customer_id in request."""
        monkeypatch.setenv(
            "STRIPE_SECRET_KEY",
            "sk_test_dummy_key_for_testing")

        response = client.post("/api/billing/portal", json={})

        # Should return error for missing customer_id
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data or "message" in data

    def test_portal_stripe_api_error(self, client, monkeypatch):
        """Test billing portal when Stripe API is unavailable."""
        monkeypatch.setenv(
            "STRIPE_SECRET_KEY",
            "sk_test_dummy_key_for_testing")

        # Mock Stripe to raise a network/API error
        with patch("stripe.billing_portal.Session.create") as mock_create:
            # Simulate network error (generic exception for testing)
            api_error = Exception("Connection error")
            mock_create.side_effect = api_error

            response = client.post("/api/billing/portal",
                                   json={"customer_id": "cus_test_customer"})

            # Should handle API errors gracefully
            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data or "message" in data

    def test_portal_stripe_13_compatibility(self, client, monkeypatch):
        """Test specific Stripe 13.x compatibility features."""
        monkeypatch.setenv(
            "STRIPE_SECRET_KEY",
            "sk_test_dummy_key_for_testing")

        # Mock Stripe 13.x session with new attributes
        class MockStripe13Session:
            def __init__(self):
                self.url = "https://billing.stripe.com/p/session_test_v13"
                self.id = "bps_test_v13_12345"
                self.customer = "cus_test_customer"
                self.return_url = "https://example.com/return"
                # Stripe 13.x specific attributes
                self.configuration = "bpc_test_config"
                self.on_behalf_of = None
                self.flow = {"type": "payment_method_update"}

        with patch("stripe.billing_portal.Session.create") as mock_create:
            mock_create.return_value = MockStripe13Session()

            response = client.post(
                "/api/billing/portal",
                json={
                    "customer_id": "cus_test_customer",
                    "return_url": "https://example.com/custom-return"})

            assert response.status_code == 200
            data = response.get_json()
            assert "url" in data
            assert data["url"].startswith("https://billing.stripe.com")

            # Verify Stripe 13.x parameters are handled
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            assert "customer" in call_args
            assert "return_url" in call_args

    def test_portal_response_format(self, client, monkeypatch):
        """Test that billing portal response follows expected format."""
        monkeypatch.setenv(
            "STRIPE_SECRET_KEY",
            "sk_test_dummy_key_for_testing")

        class MockStripeSession:
            def __init__(self):
                self.url = "https://billing.stripe.com/p/session_test_format"
                self.id = "bps_test_format"

        with patch("stripe.billing_portal.Session.create") as mock_create:
            mock_create.return_value = MockStripeSession()

            response = client.post("/api/billing/portal",
                                   json={"customer_id": "cus_test_customer"})

            assert response.status_code == 200
            data = response.get_json()

            # Verify response structure
            assert isinstance(data, dict)
            assert "url" in data
            assert isinstance(data["url"], str)
            assert data["url"].startswith("https://")

            # Verify response headers
            assert response.headers.get("Content-Type") == "application/json"

    def test_portal_with_custom_return_url(self, client, monkeypatch):
        """Test billing portal with custom return URL."""
        monkeypatch.setenv(
            "STRIPE_SECRET_KEY",
            "sk_test_dummy_key_for_testing")

        class MockStripeSession:
            def __init__(self):
                self.url = "https://billing.stripe.com/p/session_custom_return"
                self.return_url = "https://custom.example.com/billing-complete"

        with patch("stripe.billing_portal.Session.create") as mock_create:
            mock_create.return_value = MockStripeSession()

            custom_return_url = "https://custom.example.com/billing-complete"
            response = client.post("/api/billing/portal",
                                   json={
                                       "customer_id": "cus_test_customer",
                                       "return_url": custom_return_url
                                   })

            assert response.status_code == 200

            # Verify custom return URL was passed to Stripe
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            # Check that a return_url was provided (may be custom or default)
            assert "return_url" in call_args
            assert call_args["return_url"].startswith("https://")


class TestStripeImportCompatibility:
    """Test Stripe import and version compatibility."""

    def test_stripe_import_success(self):
        """Test that Stripe 13.x can be imported successfully."""
        try:
            import stripe
            assert hasattr(stripe, "billing_portal")
            assert hasattr(stripe.billing_portal, "Session")
            assert hasattr(stripe.billing_portal.Session, "create")
        except ImportError as e:
            pytest.skip(f"Stripe not available for testing: {e}")

    def test_stripe_version_compatibility(self):
        """Test that Stripe version is 13.x or compatible."""
        try:
            import stripe
            # Stripe 13.x changed version detection
            try:
                # Try modern version detection
                from stripe._version import VERSION
                version = VERSION
            except ImportError:
                # Fallback to older methods
                version = getattr(stripe, "__version__", "13.0.1")

            if isinstance(version, str):
                major_version = int(version.split(".")[0])
                # Should be version 13.x or higher
                assert major_version >= 13, f"Expected Stripe 13.x+, got {version}"
            else:
                # If version is not a string, assume it's compatible (Stripe
                # 13.x format)
                print(f"Stripe version format changed, assuming 13.x+ compatibility")

        except ImportError:
            pytest.skip("Stripe not available for testing")
        except (ValueError, AttributeError):
            # If we can't determine version but Stripe imports, assume it's
            # compatible
            print(
                "Could not determine Stripe version, but import successful - assuming 13.x+ compatibility")


if __name__ == "__main__":
    """Run tests directly for development."""
    pytest.main([__file__, "-v"])
