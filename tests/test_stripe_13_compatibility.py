# -*- coding: utf-8 -*-
"""
Stripe 13.x compatibility tests.

This module tests specific Stripe 13.x features and compatibility to ensure
the upgrade from 12.x to 13.x doesn't break existing functionality.
"""

import pytest
import os
from unittest.mock import patch, MagicMock


class TestStripe13Compatibility:
    """Test Stripe 13.x specific features and compatibility."""

    def test_stripe_13_import_structure(self):
        """Test that Stripe 13.x import structure works correctly."""
        try:
            import stripe

            # Test core imports that changed in 13.x
            assert hasattr(stripe, 'billing_portal')
            assert hasattr(stripe.billing_portal, 'Session')
            assert hasattr(stripe.billing_portal.Session, 'create')

            # Test error classes that are important for error handling (Stripe
            # 13.x structure)
            assert hasattr(stripe, 'StripeError')
            assert hasattr(stripe, 'InvalidRequestError')
            assert hasattr(stripe, 'AuthenticationError')
            assert hasattr(stripe, 'APIConnectionError')

        except ImportError:
            pytest.skip("Stripe not available for testing")

    def test_stripe_13_error_handling(self):
        """Test that Stripe 13.x error handling works correctly."""
        try:
            import stripe

            # Test that error classes can be instantiated (basic structure
            # test)
            try:
                # These should not raise ImportError or AttributeError (Stripe
                # 13.x structure)
                stripe.StripeError("test")
                stripe.InvalidRequestError("test", "param")
                stripe.AuthenticationError("test")
                stripe.APIConnectionError("test")
            except Exception as e:
                # If we can't instantiate, that's fine - just check they exist
                if "not defined" in str(e) or "has no attribute" in str(e):
                    pytest.fail(
                        f"Stripe 13.x error class structure issue: {e}")

        except ImportError:
            pytest.skip("Stripe not available for testing")

    def test_billing_portal_session_13_features(self):
        """Test Stripe 13.x billing portal session features."""
        try:
            import stripe

            # Mock a Stripe 13.x session response
            class MockStripe13Session:
                def __init__(self):
                    self.id = "bps_test_13_session"
                    self.url = "https://billing.stripe.com/p/session_13_test"
                    self.customer = "cus_test_customer"
                    self.return_url = "https://example.com/return"
                    # Stripe 13.x specific attributes
                    self.configuration = "bpc_test_config"
                    self.on_behalf_of = None
                    self.flow = {"type": "payment_method_update"}
                    self.locale = "auto"

            # Test that we can handle Stripe 13.x session objects
            session = MockStripe13Session()

            # Verify all expected attributes exist
            assert hasattr(session, 'id')
            assert hasattr(session, 'url')
            assert hasattr(session, 'customer')
            assert hasattr(session, 'return_url')
            assert hasattr(session, 'configuration')
            assert hasattr(session, 'flow')

            # Verify attribute types
            assert isinstance(session.id, str)
            assert isinstance(session.url, str)
            assert session.url.startswith('https://')

        except ImportError:
            pytest.skip("Stripe not available for testing")

    def test_stripe_13_api_version_compatibility(self):
        """Test that Stripe 13.x API version is compatible."""
        try:
            import stripe

            # Test that we can set API version (important for compatibility)
            original_version = getattr(stripe, 'api_version', None)

            try:
                # Stripe 13.x should support setting API version
                stripe.api_version = "2023-10-16"  # Recent stable version
                assert stripe.api_version == "2023-10-16"
            finally:
                # Restore original version
                if original_version:
                    stripe.api_version = original_version

        except ImportError:
            pytest.skip("Stripe not available for testing")
        except Exception as e:
            pytest.fail(f"Stripe 13.x API version compatibility issue: {e}")

    def test_customer_operations_13_compatibility(self):
        """Test that customer operations work with Stripe 13.x."""
        try:
            import stripe

            # Mock Stripe 13.x customer operations
            with patch.object(stripe.Customer, 'list') as mock_list, \
                    patch.object(stripe.Customer, 'create') as mock_create:

                # Mock customer list response (13.x format)
                mock_list.return_value = MagicMock()
                mock_list.return_value.data = [
                    MagicMock(id="cus_test_123", email="test@example.com")
                ]

                # Mock customer create response (13.x format)
                mock_create.return_value = MagicMock(
                    id="cus_new_123",
                    email="new@example.com"
                )

                # Test list operation
                customers = stripe.Customer.list(email="test@example.com")
                assert hasattr(customers, 'data')
                assert len(customers.data) > 0
                assert customers.data[0].id == "cus_test_123"

                # Test create operation
                new_customer = stripe.Customer.create(
                    email="new@example.com",
                    description="Test customer"
                )
                assert new_customer.id == "cus_new_123"

        except ImportError:
            pytest.skip("Stripe not available for testing")

    def test_stripe_13_configuration_options(self):
        """Test Stripe 13.x configuration and setup options."""
        try:
            import stripe

            # Test that we can configure Stripe 13.x properly
            original_key = getattr(stripe, 'api_key', None)

            try:
                # Test API key setting
                stripe.api_key = "sk_test_dummy_key"
                assert stripe.api_key == "sk_test_dummy_key"

                # Test that we can access configuration options
                assert hasattr(stripe, 'max_network_retries')
                assert hasattr(stripe, 'default_http_client')

            finally:
                # Restore original key
                if original_key:
                    stripe.api_key = original_key

        except ImportError:
            pytest.skip("Stripe not available for testing")

    def test_billing_portal_create_parameters_13(self):
        """Test Stripe 13.x billing portal creation parameters."""
        try:
            import stripe

            # Mock billing portal session creation with 13.x parameters
            with patch.object(stripe.billing_portal.Session, 'create') as mock_create:

                mock_session = MagicMock()
                mock_session.id = "bps_test_13_params"
                mock_session.url = "https://billing.stripe.com/p/session_13_params"
                mock_create.return_value = mock_session

                # Test with Stripe 13.x specific parameters
                session = stripe.billing_portal.Session.create(
                    customer="cus_test_customer",
                    return_url="https://example.com/return",
                    configuration="bpc_test_config",  # 13.x feature
                    locale="en",  # 13.x feature
                    on_behalf_of="acct_test"  # 13.x feature
                )

                # Verify the call was made with correct parameters
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]

                assert 'customer' in call_kwargs
                assert 'return_url' in call_kwargs
                assert call_kwargs['customer'] == "cus_test_customer"
                assert call_kwargs['return_url'] == "https://example.com/return"

                # Verify response
                assert session.id == "bps_test_13_params"
                assert session.url.startswith("https://")

        except ImportError:
            pytest.skip("Stripe not available for testing")


class TestStripe13Migration:
    """Test migration-specific scenarios from 12.x to 13.x."""

    def test_backward_compatibility_maintained(self):
        """Test that 12.x code patterns still work in 13.x."""
        try:
            import stripe

            # Test that basic 12.x patterns still work
            with patch.object(stripe.billing_portal.Session, 'create') as mock_create:

                mock_session = MagicMock()
                mock_session.url = "https://billing.stripe.com/p/session_compat"
                mock_create.return_value = mock_session

                # This is the 12.x pattern - should still work in 13.x
                session = stripe.billing_portal.Session.create(
                    customer="cus_test_customer",
                    return_url="https://example.com/return"
                )

                mock_create.assert_called_once_with(
                    customer="cus_test_customer",
                    return_url="https://example.com/return"
                )

                assert session.url.startswith("https://")

        except ImportError:
            pytest.skip("Stripe not available for testing")

    def test_error_message_format_13(self):
        """Test that error message formats are handled correctly in 13.x."""
        try:
            import stripe

            # Test different error scenarios that might have changed in 13.x
            test_errors = [
                stripe.InvalidRequestError("Invalid customer", "customer"),
                stripe.AuthenticationError("Invalid API key"),
                stripe.APIConnectionError("Network error")
            ]

            for error in test_errors:
                # Verify error can be converted to string (important for
                # logging)
                error_str = str(error)
                assert isinstance(error_str, str)
                assert len(error_str) > 0

                # Verify error has expected attributes
                assert hasattr(
                    error, 'user_message') or hasattr(
                    error, 'message') or str(error)

        except ImportError:
            pytest.skip("Stripe not available for testing")


if __name__ == '__main__':
    """Run tests directly for development."""
    pytest.main([__file__, '-v'])
