# -*- coding: utf-8 -*-
"""
Billing portal route for Stripe 13.x integration.

This module provides the billing portal endpoint that creates Stripe billing
portal sessions for customer self-service billing management.
"""

import os
import logging
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, ValidationError

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
billing_bp = Blueprint('billing', __name__, url_prefix='/api/billing')


class BillingPortalRequestSchema(Schema):
    """Schema for billing portal request validation."""
    customer_id = fields.Str(required=True,
                             validate=lambda x: x.startswith('cus_'))
    return_url = fields.Url(required=False, schemes=['https'])
    configuration = fields.Str(required=False)


@billing_bp.route('/portal', methods=['POST'])
def create_billing_portal():
    """
    Create a Stripe billing portal session.

    This endpoint creates a billing portal session for the specified customer,
    allowing them to manage their billing information, view invoices, and
    update payment methods.

    Returns:
        JSON response with billing portal URL or error message
    """
    try:
        # Validate request data
        schema = BillingPortalRequestSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as e:
            logger.warning(f"Invalid billing portal request: {e.messages}")
            return jsonify({'error': 'Invalid request data',
                           'details': e.messages}), 400

        # Check if Stripe is configured
        stripe_key = os.getenv('STRIPE_SECRET_KEY')
        if not stripe_key:
            logger.error("Stripe secret key not configured")
            return jsonify({'error': 'Billing service not configured'}), 501

        # Import and configure Stripe
        try:
            import stripe
            stripe.api_key = stripe_key
        except ImportError:
            logger.error("Stripe library not available")
            return jsonify({'error': 'Billing service unavailable'}), 500

        # Extract parameters
        customer_id = data['customer_id']
        return_url = data.get(
            'return_url',
            request.host_url.rstrip('/') +
            '/billing/complete')
        configuration = data.get('configuration')

        # Create billing portal session parameters
        session_params = {
            'customer': customer_id,
            'return_url': return_url
        }

        # Add configuration if provided (Stripe 13.x feature)
        if configuration:
            session_params['configuration'] = configuration

        # Create billing portal session
        try:
            session = stripe.billing_portal.Session.create(**session_params)

            logger.info(
                f"Created billing portal session for customer {customer_id}")

            return jsonify({
                'url': session.url,
                'session_id': session.id
            }), 200

        except stripe.InvalidRequestError as e:
            logger.warning(
                f"Invalid Stripe request for customer {customer_id}: {str(e)}")
            return jsonify({'error': 'Invalid customer or request'}), 400

        except stripe.AuthenticationError as e:
            logger.error(f"Stripe authentication error: {str(e)}")
            return jsonify(
                {'error': 'Billing service authentication failed'}), 500

        except stripe.APIConnectionError as e:
            logger.error(f"Stripe API connection error: {str(e)}")
            return jsonify(
                {'error': 'Billing service temporarily unavailable'}), 503

        except stripe.StripeError as e:
            logger.error(f"Stripe error for customer {customer_id}: {str(e)}")
            return jsonify({'error': 'Billing service error'}), 500

    except Exception as e:
        logger.error(f"Unexpected error in billing portal: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@billing_bp.route('/portal/health', methods=['GET'])
def billing_health():
    """
    Health check endpoint for billing service.

    Returns:
        JSON response indicating billing service status
    """
    try:
        # Check if Stripe is configured
        stripe_key = os.getenv('STRIPE_SECRET_KEY')
        if not stripe_key:
            return jsonify({
                'status': 'unavailable',
                'message': 'Stripe not configured'
            }), 503

        # Check if Stripe library is available
        try:
            import stripe
            stripe.api_key = stripe_key

            # Test Stripe connection with a simple API call
            stripe.Account.retrieve()

            return jsonify({
                'status': 'healthy',
                'message': 'Billing service operational',
                'stripe_version': getattr(stripe, '__version__', 'unknown')
            }), 200

        except ImportError:
            return jsonify({
                'status': 'unavailable',
                'message': 'Stripe library not available'
            }), 503

        except stripe.AuthenticationError:
            return jsonify({
                'status': 'misconfigured',
                'message': 'Stripe authentication failed'
            }), 503

        except stripe.StripeError as e:
            return jsonify({
                'status': 'degraded',
                'message': f'Stripe service issue: {str(e)}'
            }), 503

    except Exception as e:
        logger.error(f"Billing health check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Health check failed'
        }), 500


def register_billing_routes(app):
    """
    Register billing routes with the Flask application.

    Args:
        app: Flask application instance
    """
    app.register_blueprint(billing_bp)
    logger.info("Billing portal routes registered")
