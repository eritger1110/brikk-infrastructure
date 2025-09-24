# src/routes/billing.py
from __future__ import annotations

import os
from typing import Optional, Dict, Any

from flask import Blueprint, jsonify, request
from flask import current_app as log

# JWT (optional; we’ll only read identity if available)
try:
    from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
    HAVE_JWT = True
except Exception:  # pragma: no cover
    HAVE_JWT = False

# Stripe (optional – only needed for the portal)
try:
    import stripe  # type: ignore
    HAVE_STRIPE = True
except Exception:  # pragma: no cover
    HAVE_STRIPE = False

billing_bp = Blueprint("billing", __name__)  # mounted at /api in main.py


def _json() -> Dict[str, Any]:
    return (request.get_json(silent=True) or {}) if request.data else {}


@billing_bp.route("/billing/portal", methods=["POST", "OPTIONS"])
def billing_portal():
    if request.method == "OPTIONS":
        return ("", 204)

    if not HAVE_STRIPE:
        return jsonify({"error": "Stripe SDK not available on server"}), 501

    secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret:
        return jsonify({"error": "STRIPE_SECRET_KEY missing"}), 500
    stripe.api_key = secret

    return_url = os.getenv("BILLING_PORTAL_RETURN_URL", "").strip() or "https://www.getbrikk.com/app/"

    payload = _json()
    customer_id = (payload.get("customer_id") or "").strip() or None

    # Try to derive the customer from the logged-in email, unless one was provided
    email: Optional[str] = None
    if not customer_id and HAVE_JWT:
        try:
            # This is the correct API call; it accepts optional=True
            verify_jwt_in_request(optional=True)
            ident = get_jwt_identity()
            if isinstance(ident, str) and "@" in ident:
                email = ident.lower()
        except Exception:
            email = None

    try:
        if not customer_id:
            # If we know the email, find or create the Customer
            if email:
                # Basic search by email (works without Search beta)
                found = stripe.Customer.list(limit=1, email=email)
                if found.data:
                    customer_id = found.data[0].id

                if not customer_id:
                    created = stripe.Customer.create(email=email, description="Brikk user")
                    customer_id = created.id

            if not customer_id:
                return jsonify({"error": "No Stripe customer on file for this user"}), 400

        sess = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return jsonify({"url": sess.url}), 200

    except stripe.error.StripeError as e:
        msg = getattr(e, "user_message", None) or str(e)
        log.logger.error(f"Stripe error: {msg}")
        return jsonify({"error": f"Stripe error: {msg}"}), 502
    except Exception:
        log.logger.exception("Unexpected error creating portal session")
        return jsonify({"error": "Unexpected server error"}), 500
