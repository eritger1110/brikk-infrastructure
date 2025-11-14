# -*- coding: utf-8 -*-
"""
Dashboard API endpoints for Brikk dashboard frontend
Handles Auth0 authentication, user management, subscriptions, and API keys

Last updated: 2025-11-14
"""
from __future__ import annotations

import os
import secrets
from typing import Optional, Dict, Any
from datetime import datetime

from flask import Blueprint, jsonify, request, current_app
from src.infra.db import db
from src.models.user import User
from src.models.org import Organization
from src.models.api_key import ApiKey

# Import Stripe
try:
    import stripe
    HAVE_STRIPE = True
except Exception:
    HAVE_STRIPE = False

# Import Auth0 verification
try:
    from src.utils.auth0_verify import verify_auth0_token
    HAVE_AUTH0 = True
except Exception:
    HAVE_AUTH0 = False

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api")


# ============================================================================
# Helper Functions
# ============================================================================

def _json() -> Dict[str, Any]:
    """Safely parse JSON body or return empty dict."""
    return (request.get_json(silent=True) or {}) if request.data else {}


def _verify_auth0_token_from_header() -> Optional[Dict[str, Any]]:
    """
    Extract and verify Auth0 Bearer token from Authorization header
    Returns decoded token payload if valid, None otherwise
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.replace("Bearer ", "").strip()
    if not token:
        return None
    
    # Verify token with Auth0
    if HAVE_AUTH0:
        try:
            payload = verify_auth0_token(token)
            return payload
        except Exception as e:
            current_app.logger.error(f"Auth0 token verification failed: {e}")
            return None
    else:
        # Fallback: Basic JWT decode without verification (DEV ONLY)
        import jwt
        try:
            # WARNING: This does NOT verify the signature!
            # Only use this in development
            payload = jwt.decode(token, options={"verify_signature": False})
            current_app.logger.warning("Auth0 verification unavailable, using unverified token")
            return payload
        except Exception as e:
            current_app.logger.error(f"Token decode failed: {e}")
            return None


def _require_auth() -> tuple[Optional[Dict[str, Any]], Optional[tuple]]:
    """
    Verify Auth0 token and return payload
    Returns (payload, None) on success or (None, error_response) on failure
    """
    payload = _verify_auth0_token_from_header()
    if not payload:
        return None, (jsonify({"error": "Unauthorized"}), 401)
    return payload, None


def _get_or_create_user_from_auth0(auth0_payload: Dict[str, Any]) -> Optional[User]:
    """
    Get or create user from Auth0 token payload
    Returns User object or None
    """
    # Extract user info from Auth0 payload
    auth0_user_id = auth0_payload.get("sub")  # Auth0 user ID (e.g., "auth0|123456")
    email = auth0_payload.get("email") or auth0_payload.get("https://api.getbrikk.com/email")
    name = auth0_payload.get("name") or auth0_payload.get("https://api.getbrikk.com/name")
    picture = auth0_payload.get("picture") or auth0_payload.get("https://api.getbrikk.com/picture")
    
    if not auth0_user_id or not email:
        current_app.logger.error("Auth0 payload missing sub or email")
        return None
    
    # Check if user exists by auth0_user_id
    user = User.query.filter_by(auth0_user_id=auth0_user_id).first()
    
    if not user:
        # Check if user exists by email (for migration)
        user = User.query.filter_by(email=email).first()
        if user:
            # Update existing user with Auth0 ID
            user.auth0_user_id = auth0_user_id
            if name:
                user.name = name
            if picture:
                user.picture = picture
            db.session.commit()
            current_app.logger.info(f"Updated user {email} with Auth0 ID")
        else:
            # Create new user
            # First, create or get organization for this user
            org_slug = email.split("@")[0].replace(".", "-").replace("_", "-")
            org = Organization.query.filter_by(slug=org_slug).first()
            if not org:
                org = Organization(
                    name=f"{email}'s Organization",
                    slug=org_slug,
                    plan_tier="FREE",
                    subscription_status="active"
                )
                db.session.add(org)
                db.session.flush()  # Get org.id
            
            # Create username from email
            username = email.split("@")[0]
            # Ensure username is unique
            base_username = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                username=username,
                email=email,
                auth0_user_id=auth0_user_id,
                name=name,
                picture=picture,
                org_id=str(org.id),
                role="admin",  # First user in org is admin
                password_hash="auth0",  # Placeholder since Auth0 handles auth
                email_verified=True  # Auth0 verified
            )
            db.session.add(user)
            db.session.commit()
            current_app.logger.info(f"Created new user {email} with Auth0 ID")
    
    return user


# ============================================================================
# User Management Endpoints
# ============================================================================

@dashboard_bp.route("/users/sync", methods=["POST", "OPTIONS"])
def sync_user():
    """
    Sync user from Auth0 login
    Creates or updates user in database
    """
    if request.method == "OPTIONS":
        return ("", 204)
    
    # Verify Auth0 token
    payload, error = _require_auth()
    if error:
        return error
    
    # Get or create user
    user = _get_or_create_user_from_auth0(payload)
    if not user:
        return jsonify({"error": "Failed to sync user"}), 500
    
    return jsonify({
        "user_id": str(user.id),
        "org_id": str(user.org_id),
        "is_new_user": user.created_at and (datetime.utcnow() - user.created_at).seconds < 60
    }), 200


@dashboard_bp.route("/users/me", methods=["GET", "OPTIONS"])
def get_current_user():
    """
    Get current user profile
    """
    if request.method == "OPTIONS":
        return ("", 204)
    
    # Verify Auth0 token
    payload, error = _require_auth()
    if error:
        return error
    
    # Get user
    user = _get_or_create_user_from_auth0(payload)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "auth0_user_id": user.auth0_user_id,
        "org_id": str(user.org_id),
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }), 200


# ============================================================================
# Subscription Endpoints
# ============================================================================

@dashboard_bp.route("/subscriptions/current", methods=["GET", "OPTIONS"])
def get_current_subscription():
    """
    Get current organization's subscription
    """
    if request.method == "OPTIONS":
        return ("", 204)
    
    # Verify Auth0 token
    payload, error = _require_auth()
    if error:
        return error
    
    # Get user and org
    user = _get_or_create_user_from_auth0(payload)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    org = Organization.query.filter_by(id=user.org_id).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404
    
    # Return org-level subscription info
    return jsonify({
        "plan_tier": org.plan_tier or "FREE",
        "subscription_status": org.subscription_status or "active",
        "stripe_customer_id": org.stripe_customer_id,
        "stripe_subscription_id": org.stripe_subscription_id,
        "current_period_end": org.current_period_end.isoformat() if org.current_period_end else None
    }), 200


# ============================================================================
# Billing Endpoints
# ============================================================================

@dashboard_bp.route("/billing/checkout-complete", methods=["POST", "OPTIONS"])
def checkout_complete():
    """
    Validate Stripe checkout session after payment
    PUBLIC ENDPOINT - No auth required (validated via Stripe session)
    """
    if request.method == "OPTIONS":
        return ("", 204)
    
    if not HAVE_STRIPE:
        return jsonify({"error": "Stripe not available"}), 501
    
    # Initialize Stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not stripe.api_key:
        return jsonify({"error": "Stripe not configured"}), 500
    
    # Get session ID from request
    data = _json()
    session_id = data.get("session_id", "").strip()
    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400
    
    try:
        # Retrieve session from Stripe
        session = stripe.checkout.Session.retrieve(
            session_id,
            expand=["customer", "subscription", "line_items"]
        )
        
        if session.payment_status != "paid":
            return jsonify({"error": "Payment not completed"}), 400
        
        # Extract customer info
        customer_email = session.customer_details.email if session.customer_details else None
        customer_id = session.customer if isinstance(session.customer, str) else session.customer.id
        subscription_id = session.subscription if isinstance(session.subscription, str) else (session.subscription.id if session.subscription else None)
        
        # Determine plan tier from line items
        plan_tier = "STARTER"  # Default
        if session.line_items and session.line_items.data:
            price_id = session.line_items.data[0].price.id
            # Map price IDs to plan tiers
            price_to_tier = {
                os.getenv("PRICE_FREE"): "FREE",
                os.getenv("PRICE_HACKER"): "HACKER",
                os.getenv("PRICE_STARTER"): "STARTER",
                os.getenv("PRICE_PRO"): "PRO",
            }
            plan_tier = price_to_tier.get(price_id, "STARTER")
        
        # Create or update organization
        org_name = f"{customer_email}'s Organization" if customer_email else "New Organization"
        org_slug = customer_email.split("@")[0].replace(".", "-").replace("_", "-") if customer_email else "new-org"
        org = Organization.query.filter_by(stripe_customer_id=customer_id).first()
        
        if not org:
            org = Organization(
                name=org_name,
                slug=org_slug,
                plan_tier=plan_tier,
                subscription_status="active",
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id
            )
            db.session.add(org)
            db.session.flush()
        else:
            org.plan_tier = plan_tier
            org.subscription_status = "active"
            org.stripe_subscription_id = subscription_id
        
        # Create or update user
        user = None
        if customer_email:
            user = User.query.filter_by(email=customer_email).first()
            if not user:
                username = customer_email.split("@")[0]
                # Ensure username is unique
                base_username = username
                counter = 1
                while User.query.filter_by(username=username).first():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = User(
                    username=username,
                    email=customer_email,
                    name=customer_email.split("@")[0],
                    org_id=str(org.id),
                    role="admin",
                    password_hash="stripe",  # Placeholder
                    email_verified=True
                )
                db.session.add(user)
        
        # Generate API key if new org
        api_key_value = None
        if not ApiKey.query.filter_by(organization_id=org.id).first():
            api_key_value = f"brikk_live_{secrets.token_urlsafe(32)}"
            key_id = secrets.token_urlsafe(16)
            key_prefix = api_key_value[:12]
            
            # Encrypt the key
            from src.models.api_key import get_fernet
            fernet = get_fernet()
            encrypted_key = fernet.encrypt(api_key_value.encode()).decode()
            
            api_key = ApiKey(
                key_id=key_id,
                key_prefix=key_prefix,
                organization_id=org.id,
                name="Production Key",
                api_key_encrypted=encrypted_key,
                is_active=True,
                tier=plan_tier.lower()
            )
            db.session.add(api_key)
        
        db.session.commit()
        
        current_app.logger.info(f"Checkout complete: org={org.id}, plan={plan_tier}, email={customer_email}")
        
        return jsonify({
            "status": "ok",
            "plan_tier": plan_tier,
            "org_name": org.name,
            "email": customer_email,
            "api_key": api_key_value
        }), 200
        
    except stripe.StripeError as e:
        current_app.logger.error(f"Stripe error: {e}")
        return jsonify({"error": f"Stripe error: {str(e)}"}), 502
    except Exception as e:
        current_app.logger.error(f"Checkout complete error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# API Keys Endpoints
# ============================================================================

@dashboard_bp.route("/security/keys", methods=["GET", "OPTIONS"])
def list_api_keys():
    """
    Get all API keys for the current organization
    """
    if request.method == "OPTIONS":
        return ("", 204)
    
    # Verify Auth0 token
    payload, error = _require_auth()
    if error:
        return error
    
    # Get user
    user = _get_or_create_user_from_auth0(payload)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get API keys
    keys = ApiKey.query.filter_by(organization_id=user.org_id).all()
    
    # Decrypt keys
    from src.models.api_key import get_fernet
    try:
        fernet = get_fernet()
        result = []
        for key in keys:
            try:
                decrypted_key = fernet.decrypt(key.api_key_encrypted.encode()).decode()
                result.append({
                    "id": str(key.id),
                    "name": key.name,
                    "key": decrypted_key,  # Full key (only shown once in real app)
                    "created_at": key.created_at.isoformat() if key.created_at else None,
                    "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None
                })
            except Exception as e:
                current_app.logger.error(f"Failed to decrypt key {key.id}: {e}")
        return jsonify(result), 200
    except Exception as e:
        current_app.logger.error(f"Failed to get fernet: {e}")
        return jsonify([]), 200


@dashboard_bp.route("/security/keys", methods=["POST"])
def create_api_key():
    """
    Create a new API key
    """
    # Verify Auth0 token
    payload, error = _require_auth()
    if error:
        return error
    
    # Get user
    user = _get_or_create_user_from_auth0(payload)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get request data
    data = _json()
    name = data.get("name", "").strip() or "API Key"
    
    # Generate key
    key_value = f"brikk_live_{secrets.token_urlsafe(32)}"
    key_id = secrets.token_urlsafe(16)
    key_prefix = key_value[:12]
    
    # Encrypt the key
    from src.models.api_key import get_fernet
    fernet = get_fernet()
    encrypted_key = fernet.encrypt(key_value.encode()).decode()
    
    # Create key
    api_key = ApiKey(
        key_id=key_id,
        key_prefix=key_prefix,
        organization_id=user.org_id,
        name=name,
        api_key_encrypted=encrypted_key,
        is_active=True
    )
    db.session.add(api_key)
    db.session.commit()
    
    return jsonify({
        "id": str(api_key.id),
        "name": api_key.name,
        "key": key_value
    }), 201


@dashboard_bp.route("/security/keys/<int:key_id>", methods=["DELETE", "OPTIONS"])
def delete_api_key(key_id: int):
    """
    Delete an API key
    """
    if request.method == "OPTIONS":
        return ("", 204)
    
    # Verify Auth0 token
    payload, error = _require_auth()
    if error:
        return error
    
    # Get user
    user = _get_or_create_user_from_auth0(payload)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get key
    api_key = ApiKey.query.filter_by(id=key_id, organization_id=user.org_id).first()
    if not api_key:
        return jsonify({"error": "API key not found"}), 404
    
    # Delete key
    db.session.delete(api_key)
    db.session.commit()
    
    return jsonify({"success": True}), 200


# ============================================================================
# Usage Endpoints
# ============================================================================

@dashboard_bp.route("/usage/current", methods=["GET", "OPTIONS"])
def get_current_usage():
    """
    Get usage statistics for the current organization
    """
    if request.method == "OPTIONS":
        return ("", 204)
    
    # Verify Auth0 token
    payload, error = _require_auth()
    if error:
        return error
    
    # Get user
    user = _get_or_create_user_from_auth0(payload)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get org
    org = Organization.query.filter_by(id=user.org_id).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404
    
    # Return usage from org
    return jsonify({
        "requests_used": org.current_month_requests,
        "requests_limit": org.monthly_request_limit,
        "agents_count": len(org.agents) if org.agents else 0,
        "flows_count": len(org.workflows) if org.workflows else 0,
        "current_period_start": datetime.utcnow().replace(day=1).isoformat(),
        "current_period_end": datetime.utcnow().replace(day=28).isoformat()
    }), 200


# ============================================================================
# Health Check Endpoint (for testing blueprint registration)
# ============================================================================

@dashboard_bp.route("/dashboard/health", methods=["GET"])
def dashboard_health():
    """Simple health check to verify dashboard blueprint is registered"""
    return jsonify({
        "status": "ok",
        "message": "Dashboard API is running",
        "blueprint": "dashboard",
        "url_prefix": "/api"
    }), 200
