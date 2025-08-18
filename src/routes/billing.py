from flask import Blueprint, request, jsonify, current_app
from src.models.agent import db
from src.models.user import User, Subscription
from src.routes.auth import authenticate_user
import stripe
import os
from datetime import datetime

billing_bp = Blueprint('billing', __name__)

# Initialize Stripe (you'll need to set these environment variables)
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_...')  # Replace with your Stripe secret key

# Stripe Price IDs for each plan (you'll need to create these in Stripe Dashboard)
STRIPE_PRICE_IDS = {
    'hacker': 'price_hacker_monthly',  # Replace with actual Stripe price ID
    'starter': 'price_starter_monthly',  # Replace with actual Stripe price ID
    'professional': 'price_professional_monthly',  # Replace with actual Stripe price ID
    'enterprise': 'price_enterprise_monthly'  # Replace with actual Stripe price ID
}

@billing_bp.route('/plans', methods=['GET'])
def get_plans():
    """Get available billing plans"""
    plans = {
        'free': {
            'name': 'Free',
            'price': 0,
            'currency': 'USD',
            'interval': 'month',
            'features': {
                'api_calls': 1000,
                'agents': 2,
                'support': 'Community',
                'analytics': 'Basic',
                'sla': None
            }
        },
        'hacker': {
            'name': 'Hacker',
            'price': 49,
            'currency': 'USD',
            'interval': 'month',
            'features': {
                'api_calls': 7500,
                'agents': 3,
                'support': 'Email',
                'analytics': 'Basic',
                'sla': None
            }
        },
        'starter': {
            'name': 'Starter',
            'price': 99,
            'currency': 'USD',
            'interval': 'month',
            'features': {
                'api_calls': 10000,
                'agents': 5,
                'support': 'Email',
                'analytics': 'Advanced',
                'sla': '99.9%'
            }
        },
        'professional': {
            'name': 'Professional',
            'price': 299,
            'currency': 'USD',
            'interval': 'month',
            'features': {
                'api_calls': 100000,
                'agents': 25,
                'support': 'Phone + Email',
                'analytics': 'Advanced',
                'sla': '99.95%'
            }
        },
        'enterprise': {
            'name': 'Enterprise',
            'price': 'Custom',
            'currency': 'USD',
            'interval': 'month',
            'features': {
                'api_calls': 'Unlimited',
                'agents': 'Unlimited',
                'support': 'Dedicated Success Manager',
                'analytics': 'Custom',
                'sla': '99.99%'
            }
        }
    }
    
    return jsonify({'plans': plans}), 200

@billing_bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Create a Stripe checkout session for subscription"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        user = authenticate_user(auth_header)
        
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        data = request.get_json()
        plan = data.get('plan')
        
        if plan not in STRIPE_PRICE_IDS:
            return jsonify({'error': 'Invalid plan selected'}), 400
        
        # Create or get Stripe customer
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}",
                metadata={
                    'user_id': user.id,
                    'company': user.company or ''
                }
            )
            user.stripe_customer_id = customer.id
            db.session.commit()
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': STRIPE_PRICE_IDS[plan],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.host_url + 'billing/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.host_url + 'billing/cancel',
            metadata={
                'user_id': user.id,
                'plan': plan
            }
        )
        
        return jsonify({
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id
        }), 200
        
    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@billing_bp.route('/create-portal-session', methods=['POST'])
def create_portal_session():
    """Create a Stripe customer portal session"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        user = authenticate_user(auth_header)
        
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        if not user.stripe_customer_id:
            return jsonify({'error': 'No billing account found'}), 404
        
        # Create portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=request.host_url + 'dashboard'
        )
        
        return jsonify({
            'portal_url': portal_session.url
        }), 200
        
    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@billing_bp.route('/subscription', methods=['GET'])
def get_subscription():
    """Get user's current subscription"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        user = authenticate_user(auth_header)
        
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Get active subscription
        subscription = user.subscriptions.filter_by(status='active').first()
        
        if not subscription:
            return jsonify({
                'subscription': None,
                'plan': user.plan,
                'status': 'free'
            }), 200
        
        return jsonify({
            'subscription': subscription.to_dict(),
            'plan': user.plan,
            'status': subscription.status
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@billing_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session_completed(session)
    
    elif event['type'] == 'customer.subscription.created':
        subscription = event['data']['object']
        handle_subscription_created(subscription)
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)
    
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        handle_payment_succeeded(invoice)
    
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        handle_payment_failed(invoice)
    
    return jsonify({'status': 'success'}), 200

def handle_checkout_session_completed(session):
    """Handle successful checkout session"""
    try:
        user_id = session['metadata']['user_id']
        plan = session['metadata']['plan']
        
        user = User.query.get(user_id)
        if user:
            user.plan = plan
            db.session.commit()
            
    except Exception as e:
        print(f"Error handling checkout session: {e}")

def handle_subscription_created(stripe_subscription):
    """Handle new subscription creation"""
    try:
        customer_id = stripe_subscription['customer']
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        
        if user:
            subscription = Subscription(
                user_id=user.id,
                stripe_subscription_id=stripe_subscription['id'],
                stripe_customer_id=customer_id,
                plan=user.plan,
                status=stripe_subscription['status'],
                current_period_start=datetime.fromtimestamp(stripe_subscription['current_period_start']),
                current_period_end=datetime.fromtimestamp(stripe_subscription['current_period_end'])
            )
            
            db.session.add(subscription)
            db.session.commit()
            
    except Exception as e:
        print(f"Error handling subscription creation: {e}")

def handle_subscription_updated(stripe_subscription):
    """Handle subscription updates"""
    try:
        subscription = Subscription.query.filter_by(
            stripe_subscription_id=stripe_subscription['id']
        ).first()
        
        if subscription:
            subscription.status = stripe_subscription['status']
            subscription.current_period_start = datetime.fromtimestamp(stripe_subscription['current_period_start'])
            subscription.current_period_end = datetime.fromtimestamp(stripe_subscription['current_period_end'])
            subscription.cancel_at_period_end = stripe_subscription['cancel_at_period_end']
            
            db.session.commit()
            
    except Exception as e:
        print(f"Error handling subscription update: {e}")

def handle_subscription_deleted(stripe_subscription):
    """Handle subscription cancellation"""
    try:
        subscription = Subscription.query.filter_by(
            stripe_subscription_id=stripe_subscription['id']
        ).first()
        
        if subscription:
            subscription.status = 'canceled'
            subscription.user.plan = 'free'  # Downgrade to free plan
            
            db.session.commit()
            
    except Exception as e:
        print(f"Error handling subscription deletion: {e}")

def handle_payment_succeeded(invoice):
    """Handle successful payment"""
    try:
        # Update subscription status if needed
        subscription_id = invoice['subscription']
        if subscription_id:
            subscription = Subscription.query.filter_by(
                stripe_subscription_id=subscription_id
            ).first()
            
            if subscription:
                subscription.status = 'active'
                db.session.commit()
                
    except Exception as e:
        print(f"Error handling payment success: {e}")

def handle_payment_failed(invoice):
    """Handle failed payment"""
    try:
        # Update subscription status
        subscription_id = invoice['subscription']
        if subscription_id:
            subscription = Subscription.query.filter_by(
                stripe_subscription_id=subscription_id
            ).first()
            
            if subscription:
                subscription.status = 'past_due'
                db.session.commit()
                
    except Exception as e:
        print(f"Error handling payment failure: {e}")

@billing_bp.route('/usage-analytics', methods=['GET'])
def get_usage_analytics():
    """Get detailed usage analytics for billing"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        user = authenticate_user(auth_header)
        
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Get query parameters
        days = int(request.args.get('days', 30))
        
        # Calculate date range
        from datetime import datetime, timedelta
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get usage logs
        usage_logs = user.usage_logs.filter(
            UsageLog.created_at >= start_date,
            UsageLog.created_at <= end_date
        ).all()
        
        # Calculate billing metrics
        total_calls = len(usage_logs)
        successful_calls = len([log for log in usage_logs if log.status_code and log.status_code < 400])
        
        # Calculate costs (example: $0.01 per API call)
        cost_per_call = 0.01
        total_cost = total_calls * cost_per_call
        
        # Group by day for billing chart
        daily_usage = {}
        daily_costs = {}
        for log in usage_logs:
            day = log.created_at.date().isoformat()
            if day not in daily_usage:
                daily_usage[day] = 0
                daily_costs[day] = 0
            daily_usage[day] += 1
            daily_costs[day] += cost_per_call
        
        # Get plan limits and current usage
        plan_limits = user.get_plan_limits()
        current_month_usage = user.get_current_usage()
        
        return jsonify({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'usage_summary': {
                'total_calls': total_calls,
                'successful_calls': successful_calls,
                'success_rate': (successful_calls / max(total_calls, 1)) * 100,
                'current_month_usage': current_month_usage,
                'plan_limit': plan_limits['api_calls'],
                'usage_percentage': (current_month_usage / max(plan_limits['api_calls'], 1)) * 100 if plan_limits['api_calls'] != -1 else 0
            },
            'billing_summary': {
                'total_cost': round(total_cost, 2),
                'cost_per_call': cost_per_call,
                'currency': 'USD'
            },
            'daily_usage': daily_usage,
            'daily_costs': daily_costs,
            'plan_info': {
                'current_plan': user.plan,
                'plan_limits': plan_limits
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

