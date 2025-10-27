# -*- coding: utf-8 -*-
"""
Stripe Webhook Handler (Phase 8).

Handles Stripe webhook events for subscription lifecycle management.
"""
import os
import stripe
from flask import Blueprint, request, jsonify, current_app
from src.models.api_key import APIKey, db
from src.models.user import User
from src.services.api_key_service import APIKeyService

stripe_webhooks_bp = Blueprint('stripe_webhooks', __name__)


@stripe_webhooks_bp.route('/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events.
    
    Events handled:
    - customer.subscription.created: Create API key for new subscriber
    - customer.subscription.updated: Update subscription details
    - customer.subscription.deleted: Revoke API key access
    - invoice.payment_succeeded: Reset usage counters
    - invoice.payment_failed: Send notification, apply soft limit
    """
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    if not webhook_secret:
        current_app.logger.error("STRIPE_WEBHOOK_SECRET not configured")
        return jsonify({'error': 'Webhook not configured'}), 500
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        current_app.logger.error("Invalid webhook payload")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        current_app.logger.error("Invalid webhook signature")
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    event_type = event['type']
    data = event['data']['object']
    
    current_app.logger.info(f"Received Stripe webhook: {event_type}")
    
    try:
        if event_type == 'customer.subscription.created':
            handle_subscription_created(data)
        elif event_type == 'customer.subscription.updated':
            handle_subscription_updated(data)
        elif event_type == 'customer.subscription.deleted':
            handle_subscription_deleted(data)
        elif event_type == 'invoice.payment_succeeded':
            handle_payment_succeeded(data)
        elif event_type == 'invoice.payment_failed':
            handle_payment_failed(data)
        else:
            current_app.logger.info(f"Unhandled event type: {event_type}")
    
    except Exception as e:
        current_app.logger.exception(f"Error handling webhook {event_type}")
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'status': 'success'}), 200


def handle_subscription_created(subscription):
    """
    Handle new subscription creation.
    
    Creates an API key for the user with the appropriate tier.
    """
    customer_id = subscription['customer']
    subscription_id = subscription['id']
    status = subscription['status']
    
    # Get customer details
    try:
        customer = stripe.Customer.retrieve(customer_id)
        email = customer['email']
    except Exception as e:
        current_app.logger.error(f"Failed to retrieve customer {customer_id}: {e}")
        return
    
    if not email:
        current_app.logger.error(f"No email for customer {customer_id}")
        return
    
    # Determine subscription tier from price ID
    tier = get_tier_from_subscription(subscription)
    
    # Find or create user
    user = User.query.filter_by(email=email).first()
    if not user:
        current_app.logger.warning(f"User not found for email {email}, creating new user")
        user = User(
            username=email.split('@')[0],
            email=email
        )
        db.session.add(user)
        db.session.commit()
    
    # Create API key if user doesn't have one
    existing_key = APIKey.query.filter_by(user_id=user.id, is_active=True).first()
    if not existing_key:
        api_key_service = APIKeyService()
        result = api_key_service.create_key(
            user_id=user.id,
            name=f"{tier.capitalize()} API Key",
            tier=tier,
            stripe_subscription_id=subscription_id
        )
        
        if 'error' in result:
            current_app.logger.error(f"Failed to create API key: {result['error']}")
        else:
            current_app.logger.info(f"Created API key for user {email} (tier: {tier})")
            
            # TODO: Send welcome email with API key
            # send_welcome_email(email, result['api_key'])
    else:
        # Update existing key with new subscription
        existing_key.tier = tier
        existing_key.stripe_subscription_id = subscription_id
        db.session.commit()
        current_app.logger.info(f"Updated existing API key for user {email}")


def handle_subscription_updated(subscription):
    """
    Handle subscription updates (plan changes, status changes).
    """
    subscription_id = subscription['id']
    status = subscription['status']
    tier = get_tier_from_subscription(subscription)
    
    # Find API key by subscription ID
    api_key = APIKey.query.filter_by(stripe_subscription_id=subscription_id).first()
    if not api_key:
        current_app.logger.warning(f"No API key found for subscription {subscription_id}")
        return
    
    # Update tier and status
    api_key.tier = tier
    
    if status in ['active', 'trialing']:
        api_key.is_active = True
    elif status in ['canceled', 'unpaid', 'past_due']:
        api_key.is_active = False
    
    db.session.commit()
    current_app.logger.info(f"Updated API key for subscription {subscription_id}: tier={tier}, status={status}")


def handle_subscription_deleted(subscription):
    """
    Handle subscription cancellation.
    
    Deactivates the associated API key.
    """
    subscription_id = subscription['id']
    
    # Find and deactivate API key
    api_key = APIKey.query.filter_by(stripe_subscription_id=subscription_id).first()
    if api_key:
        api_key.is_active = False
        db.session.commit()
        current_app.logger.info(f"Deactivated API key for canceled subscription {subscription_id}")
    else:
        current_app.logger.warning(f"No API key found for subscription {subscription_id}")


def handle_payment_succeeded(invoice):
    """
    Handle successful payment.
    
    Resets usage counters for the billing period.
    """
    subscription_id = invoice.get('subscription')
    if not subscription_id:
        return
    
    # Find API key
    api_key = APIKey.query.filter_by(stripe_subscription_id=subscription_id).first()
    if api_key:
        # Reset monthly usage counters
        api_key.requests_this_month = 0
        api_key.cost_this_month = 0.0
        db.session.commit()
        current_app.logger.info(f"Reset usage counters for subscription {subscription_id}")


def handle_payment_failed(invoice):
    """
    Handle failed payment.
    
    Sends notification and applies soft limit.
    """
    subscription_id = invoice.get('subscription')
    if not subscription_id:
        return
    
    # Find API key
    api_key = APIKey.query.filter_by(stripe_subscription_id=subscription_id).first()
    if api_key:
        # Apply soft limit (don't deactivate yet, give them a grace period)
        current_app.logger.warning(f"Payment failed for subscription {subscription_id}")
        
        # TODO: Send payment failed email
        # send_payment_failed_email(api_key.user.email)
        
        # Optionally set a flag for soft limit
        # api_key.payment_failed = True
        # db.session.commit()


def get_tier_from_subscription(subscription):
    """
    Determine subscription tier from price ID.
    
    Returns: 'free', 'starter', 'pro', or 'hacker'
    """
    items = subscription.get('items', {}).get('data', [])
    if not items:
        return 'free'
    
    price_id = items[0]['price']['id']
    
    # Map price IDs to tiers
    price_free = os.getenv('PRICE_FREE', '')
    price_starter = os.getenv('PRICE_STARTER', '')
    price_pro = os.getenv('PRICE_PRO', '')
    price_hacker = os.getenv('PRICE_HACKER', '')
    
    if price_id == price_free:
        return 'free'
    elif price_id == price_starter:
        return 'starter'
    elif price_id == price_pro:
        return 'pro'
    elif price_id == price_hacker:
        return 'hacker'
    else:
        current_app.logger.warning(f"Unknown price ID: {price_id}, defaulting to 'free'")
        return 'free'

