# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from typing import Optional, Dict, Any

from flask import Blueprint, jsonify, request, current_app

# JWT is optional; we'll read email if present
try:
    from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
    HAVE_JWT = True
except Exception:  # pragma: no cover
    HAVE_JWT = False

# Stripe is only needed for the portal route here
try:
    import stripe  # type: ignore
    HAVE_STRIPE = True
except Exception:  # pragma: no cover
    HAVE_STRIPE = False

billing_bp = Blueprint("billing", __name__)  # mounted at /api in main.py


def _json() -> Dict[str, Any]:
    """Safely parse JSON body or return empty dict."""
    return (request.get_json(silent=True) or {}) if request.data else {}


@billing_bp.route("/billing/portal", methods=["POST", "OPTIONS"])
def billing_portal():
    """Creates a Stripe billing portal session for the current user."""
    if request.method == "OPTIONS":
        return ("", 204)

    if not HAVE_STRIPE:
        return jsonify({"error": "Stripe SDK not available on server"}), 501

    secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret:
        return jsonify({"error": "STRIPE_SECRET_KEY missing"}), 500
    stripe.api_key = secret

    return_url = (
        os.getenv("BILLING_PORTAL_RETURN_URL", "").strip()
        or "https://www.getbrikk.com/app/"
    )

    payload = _json()
    customer_id = (payload.get("customer_id") or "").strip() or None

    # Try to derive the customer from the logged-in email, unless one was
    # provided
    email: Optional[str] = None
    if not customer_id and HAVE_JWT:
        try:
            # v4 syntax: pass optional=True (no exception if no JWT)
            verify_jwt_in_request(optional=True)
            ident = get_jwt_identity()
            if isinstance(ident, str) and "@" in ident:
                email = ident.lower()
        except Exception:
            email = None

    try:
        if not customer_id:
            if email:
                # find-or-create by email
                found = stripe.Customer.list(limit=1, email=email)
                if found.data:
                    customer_id = found.data[0].id
                if not customer_id:
                    created = stripe.Customer.create(
                        email=email, description="Brikk user"
                    )
                    customer_id = created.id

            if not customer_id:
                return jsonify(
                    {"error": "No Stripe customer on file for this user"}), 400

        sess = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        current_app.logger.info(f"[billing] portal for customer={customer_id}")
        return jsonify({"url": sess.url}), 200

    except stripe.StripeError as e:
        msg = getattr(e, "user_message", None) or str(e)
        current_app.logger.error(f"Stripe error: {msg}")
        return jsonify({"error": f"Stripe error: {msg}"}), 502
    except Exception:
        current_app.logger.exception(
            "Unexpected error creating portal session")
        return jsonify({"error": "Unexpected server error"}), 500



@billing_bp.route("/billing/create-checkout-session", methods=["POST", "OPTIONS"])
def create_checkout_session():
    """Creates a Stripe Checkout session for subscription signup."""
    if request.method == "OPTIONS":
        return ("", 204)

    if not HAVE_STRIPE:
        return jsonify({"error": "Stripe SDK not available on server"}), 501

    secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret:
        return jsonify({"error": "STRIPE_SECRET_KEY missing"}), 500
    stripe.api_key = secret

    payload = _json()
    price_id = payload.get("price_id", "").strip()
    success_url = payload.get("success_url", "").strip()
    cancel_url = payload.get("cancel_url", "").strip()

    if not price_id or not success_url or not cancel_url:
        return jsonify({"error": "Missing required fields: price_id, success_url, cancel_url"}), 400

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            allow_promotion_codes=True,
            billing_address_collection="auto",
        )
        
        current_app.logger.info(f"[billing] Created checkout session: {session.id}")
        return jsonify({"session_id": session.id}), 200

    except stripe.StripeError as e:
        msg = getattr(e, "user_message", None) or str(e)
        current_app.logger.error(f"Stripe error: {msg}")
        return jsonify({"error": f"Stripe error: {msg}"}), 502
    except Exception:
        current_app.logger.exception("Unexpected error creating checkout session")
        return jsonify({"error": "Unexpected server error"}), 500

# Force redeploy Mon Oct 27 14:22:19 EDT 2025
