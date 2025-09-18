# src/routes/app.py
import os
from typing import Any, Dict

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

import stripe

app_bp = Blueprint("app", __name__)

# ---------- Stripe setup ----------
stripe.api_key = (os.getenv("STRIPE_SECRET") or "").strip()

def _create_billing_portal_session(**kwargs):
    """
    Stripe SDK compatibility:
    - v12+: stripe.billing_portal.sessions.create(...)
    - older: stripe.billing_portal.Session.create(...)
    """
    try:
        return stripe.billing_portal.sessions.create(**kwargs)  # v12+
    except AttributeError:
        return stripe.billing_portal.Session.create(**kwargs)   # older


# ---------- Billing Portal ----------
@app_bp.post("/billing/portal")
@jwt_required(optional=True)
def billing_portal():
    if not stripe.api_key:
        # Matches the “Stripe not configured” error you saw in the console.
        return jsonify({"error": "Stripe not configured"}), 501

    # Identify current user (adjust to your identity payload structure).
    ident = get_jwt_identity() or {}
    email = None
    if isinstance(ident, dict):
        email = ident.get("email")

    # If your user model stores stripe_customer_id, you can accept/forward it.
    customer_id = None
    if request.is_json:
        customer_id = (request.json or {}).get("customer_id")

    try:
        # Fallback: try locating the customer by email if not provided/stored.
        if not customer_id and email:
            found = stripe.customers.search(query=f"email:'{email}'", limit=1)
            if found.data:
                customer_id = found.data[0].id

        if not customer_id:
            return jsonify({"error": "No Stripe customer found for this user"}), 404

        return_url = (os.getenv("BILLING_PORTAL_RETURN_URL") or "https://www.getbrikk.com/app/").strip()
        sess = _create_billing_portal_session(customer=customer_id, return_url=return_url)
        return jsonify({"url": sess.url}), 200

    except stripe.error.StripeError as e:
        return jsonify({"error": e.user_message or str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------- Dashboard: Metrics (demo) ----------
@app_bp.get("/metrics")
@jwt_required(optional=True)
def metrics():
    # Simple synthetic data so the charts render.
    demo = {
        "series": {
            "last10m": [2, 3, 5, 4, 6, 7, 4, 6, 5, 8],
            "latency": [220, 210, 230, 190, 200, 240, 210, 220, 205, 215],
        }
    }
    return jsonify(demo), 200


# ---------- Demo Workflows ----------
@app_bp.post("/workflows/<workflow>/execute")
@jwt_required(optional=True)
def run_workflow(workflow: str):
    # Echo back something friendly so the UI shows results.
    ident = get_jwt_identity() or {}
    as_email = ident.get("email") if i_
