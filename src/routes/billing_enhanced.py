# -*- coding: utf-8 -*-
"""
Enhanced billing routes for subscription and plan management.
Extends existing billing.py with additional endpoints for the dashboard.
"""
import os
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from src.database import db
from src.models.org import Organization

try:
    import stripe
    HAVE_STRIPE = True
except ImportError:
    HAVE_STRIPE = False

billing_enhanced_bp = Blueprint("billing_enhanced", __name__, url_prefix="/api/billing")


# Define available plans
PLANS = [
    {
        "id": "free",
        "name": "Free",
        "price": 0,
        "interval": "month",
        "features": [
            "Up to 5 agents",
            "100 workflows/month",
            "Basic integrations",
            "Community support"
        ],
        "limits": {
            "agents": 5,
            "workflows": 100,
            "executions": 1000
        }
    },
    {
        "id": "pro",
        "name": "Pro",
        "price": 49,
        "interval": "month",
        "features": [
            "Unlimited agents",
            "Unlimited workflows",
            "All integrations",
            "Priority support",
            "Advanced analytics"
        ],
        "limits": {
            "agents": -1,  # unlimited
            "workflows": -1,
            "executions": -1
        },
        "stripe_price_id": os.getenv("STRIPE_PRO_PRICE_ID", "price_pro")
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "price": 299,
        "interval": "month",
        "features": [
            "Everything in Pro",
            "Dedicated support",
            "Custom integrations",
            "SLA guarantee",
            "On-premise deployment"
        ],
        "limits": {
            "agents": -1,
            "workflows": -1,
            "executions": -1
        },
        "stripe_price_id": os.getenv("STRIPE_ENTERPRISE_PRICE_ID", "price_enterprise")
    }
]


@billing_enhanced_bp.get("/plans")
def get_plans():
    """
    Get available subscription plans.
    GET /api/billing/plans
    """
    return jsonify({"plans": PLANS}), 200


@billing_enhanced_bp.get("/subscription")
@jwt_required()
def get_subscription():
    """
    Get current organization's subscription details.
    GET /api/billing/subscription
    """
    claims = get_jwt()
    org_id = claims.get("org_id")
    
    if not org_id:
        return jsonify({"error": "No organization associated with user"}), 400
    
    org = Organization.query.filter_by(id=org_id).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404
    
    # Build subscription response
    subscription = {
        "plan": org.plan_tier or "FREE",
        "status": org.subscription_status or "active",
        "current_period_end": org.current_period_end.isoformat() if org.current_period_end else None,
        "stripe_customer_id": org.stripe_customer_id,
        "stripe_subscription_id": org.stripe_subscription_id
    }
    
    # If Stripe is available and we have a subscription ID, fetch live data
    if HAVE_STRIPE and org.stripe_subscription_id:
        try:
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
            stripe_sub = stripe.Subscription.retrieve(org.stripe_subscription_id)
            subscription["status"] = stripe_sub.status
            subscription["current_period_end"] = stripe_sub.current_period_end
            subscription["cancel_at_period_end"] = stripe_sub.cancel_at_period_end
        except Exception as e:
            print(f"Failed to fetch Stripe subscription: {e}")
    
    return jsonify(subscription), 200


@billing_enhanced_bp.post("/checkout")
@jwt_required()
def create_checkout():
    """
    Create a Stripe checkout session for plan upgrade.
    POST /api/billing/checkout
    Body: {"plan_id": "pro"}
    """
    if not HAVE_STRIPE:
        return jsonify({"error": "Stripe not configured"}), 501
    
    claims = get_jwt()
    org_id = claims.get("org_id")
    user_email = claims.get("email")
    
    if not org_id:
        return jsonify({"error": "No organization associated with user"}), 400
    
    org = Organization.query.filter_by(id=org_id).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404
    
    data = request.get_json() or {}
    plan_id = data.get("plan_id", "").lower()
    
    # Find plan
    plan = next((p for p in PLANS if p["id"] == plan_id), None)
    if not plan or plan_id == "free":
        return jsonify({"error": "Invalid plan"}), 400
    
    if "stripe_price_id" not in plan:
        return jsonify({"error": "Plan not available for purchase"}), 400
    
    try:
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        
        # Get or create Stripe customer
        customer_id = org.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(
                email=user_email,
                metadata={
                    "org_id": org_id,
                    "org_name": org.name
                }
            )
            customer_id = customer.id
            org.stripe_customer_id = customer_id
            db.session.commit()
        
        # Create checkout session
        success_url = os.getenv("STRIPE_SUCCESS_URL", "https://brikkdashboardfe.netlify.app/billing?success=true")
        cancel_url = os.getenv("STRIPE_CANCEL_URL", "https://brikkdashboardfe.netlify.app/plans")
        
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{
                "price": plan["stripe_price_id"],
                "quantity": 1
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            allow_promotion_codes=True,
            billing_address_collection="auto",
            metadata={
                "org_id": org_id,
                "plan_id": plan_id
            }
        )
        
        return jsonify({
            "session_id": session.id,
            "url": session.url
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to create checkout session: {str(e)}"}), 500


@billing_enhanced_bp.post("/cancel")
@jwt_required()
def cancel_subscription():
    """
    Cancel the current subscription.
    POST /api/billing/cancel
    """
    if not HAVE_STRIPE:
        return jsonify({"error": "Stripe not configured"}), 501
    
    claims = get_jwt()
    org_id = claims.get("org_id")
    
    # Check admin permission
    roles = claims.get("roles", [])
    if not any(r in ["admin", "owner"] for r in roles):
        return jsonify({"error": "Admin access required"}), 403
    
    if not org_id:
        return jsonify({"error": "No organization associated with user"}), 400
    
    org = Organization.query.filter_by(id=org_id).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404
    
    if not org.stripe_subscription_id:
        return jsonify({"error": "No active subscription"}), 400
    
    try:
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        
        # Cancel at period end (don't immediately cancel)
        subscription = stripe.Subscription.modify(
            org.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        org.subscription_status = "canceling"
        db.session.commit()
        
        return jsonify({
            "message": "Subscription will be canceled at period end",
            "cancel_at": subscription.current_period_end
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to cancel subscription: {str(e)}"}), 500


@billing_enhanced_bp.put("/payment-method")
@jwt_required()
def update_payment_method():
    """
    Update payment method (redirects to Stripe billing portal).
    PUT /api/billing/payment-method
    """
    if not HAVE_STRIPE:
        return jsonify({"error": "Stripe not configured"}), 501
    
    claims = get_jwt()
    org_id = claims.get("org_id")
    
    if not org_id:
        return jsonify({"error": "No organization associated with user"}), 400
    
    org = Organization.query.filter_by(id=org_id).first()
    if not org or not org.stripe_customer_id:
        return jsonify({"error": "No billing account found"}), 404
    
    try:
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        
        return_url = os.getenv("BILLING_PORTAL_RETURN_URL", "https://brikkdashboardfe.netlify.app/billing")
        
        session = stripe.billing_portal.Session.create(
            customer=org.stripe_customer_id,
            return_url=return_url
        )
        
        return jsonify({"url": session.url}), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to create portal session: {str(e)}"}), 500
