# src/routes/app.py
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request
from flask import current_app as log

# Optional JWT (we only read identity/email if available)
try:
    from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
    HAVE_JWT = True
except Exception:  # pragma: no cover
    HAVE_JWT = False

# Optional Stripe (only needed for billing portal)
try:
    import stripe  # type: ignore
    HAVE_STRIPE = True
except Exception:  # pragma: no cover
    HAVE_STRIPE = False

app_bp = Blueprint("app", __name__)  # mounted at /api in main.py


def _json() -> Dict[str, Any]:
    return (request.get_json(silent=True) or {}) if request.data else {}


# --------------------------------------------------------------------------- #
# Metrics (demo)
# --------------------------------------------------------------------------- #
@app_bp.route("/metrics", methods=["GET"])
def metrics():
    return jsonify({
        "requests": [2, 3, 5, 4, 6, 7, 4, 6, 5, 8],
        "latency_ms": [220, 210, 230, 190, 200, 240, 210, 220, 205, 215],
    }), 200


# --------------------------------------------------------------------------- #
# Demo workflows
# --------------------------------------------------------------------------- #
@app_bp.route("/workflows/<workflow>/execute", methods=["POST", "OPTIONS"])
def execute_workflow(workflow: str):
    if request.method == "OPTIONS":
        return ("", 204)

    payload = _json()
    ran_as: Optional[str] = None

    if HAVE_JWT:
        try:
            verify_jwt_in_request(optional=True)
            ident = get_jwt_identity()
            if isinstance(ident, str):
                ran_as = ident
        except Exception:
            ran_as = None

    # Echo a trivial result
    return jsonify({
        "ok": True,
        "workflow": workflow,
        "echo": {"demo": bool(payload.get("demo", True))},
        "ran_as": ran_as,
        "result": f"demo result for '{workflow}'",
    }), 200


# --------------------------------------------------------------------------- #
# Billing portal (Stripe)
# - Finds/creates the Customer by logged-in email (JWT) unless a customer_id
#   is explicitly provided in the POST body.
# --------------------------------------------------------------------------- #
@app_bp.route("/billing/portal", methods=["POST", "OPTIONS"])
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
            verify_jwt_in_request(optional=True)
            ident = get_jwt_identity()
            if isinstance(ident, str) and "@" in ident:
                email = ident.lower()
        except Exception:
            pass

    try:
        if not customer_id:
            # 1) Look up by email if we have one
            if email:
                # Use search if available, else list filter
                try:
                    # Customer.search requires search beta; fallback to list
                    found = stripe.Customer.list(limit=1, email=email)
                    if found.data:
                        customer_id = found.data[0].id
                except Exception:
                    # Fallback again (should rarely be needed)
                    found = stripe.Customer.list(limit=10)
                    for c in found.auto_paging_iter():
                        if (c.get("email") or "").lower() == email:
                            customer_id = c["id"]
                            break

                # 2) Create if still missing
                if not customer_id:
                    created = stripe.Customer.create(email=email, description="Brikk user")
                    customer_id = created.id

            # If we STILL don't have a customer_id, error out with a clear message
            if not customer_id:
                return jsonify({"error": "No Stripe customer on file for this user"}), 400

        # Create a Customer Portal session
        sess = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return jsonify({"url": sess.url}), 200

    except stripe.InvalidRequestError as e:
        # Handle invalid customer ID or request parameters
        log.logger.warning(f"Invalid Stripe request: {str(e)}")
        return jsonify({"error": "Invalid customer or request parameters"}), 400
    except stripe.AuthenticationError as e:
        # Handle authentication errors
        log.logger.error(f"Stripe authentication error: {str(e)}")
        return jsonify({"error": "Billing service authentication failed"}), 500
    except stripe.APIConnectionError as e:
        # Handle network/connection errors
        log.logger.error(f"Stripe API connection error: {str(e)}")
        return jsonify({"error": "Billing service temporarily unavailable"}), 503
    except stripe.StripeError as e:
        # Handle other Stripe-specific errors (Stripe 13.x compatible)
        log.logger.error(f"Stripe error: {str(e)}")
        return jsonify({"error": f"Billing service error: {str(e)}"}), 502
    except Exception as e:
        # Handle general errors
        log.logger.exception("Unexpected error creating portal session")
        return jsonify({"error": "Unexpected server error"}), 500


# --------------------------------------------------------------------------- #
# API Key (demo)
# - Returns a deterministic per-user "API key" so the frontend can display one.
#   This is NOT a real credential; replace with a DB-backed token when ready.
# --------------------------------------------------------------------------- #
@app_bp.route("/key", methods=["GET", "OPTIONS"])
def get_api_key():
    if request.method == "OPTIONS":
        return ("", 204)

    # Require auth: we expect a JWT cookie
    email: Optional[str] = None
    if HAVE_JWT:
        try:
            verify_jwt_in_request(optional=False)
            ident = get_jwt_identity()
            if isinstance(ident, str) and "@" in ident:
                email = ident.lower()
        except Exception:
            return jsonify({"error": "unauthorized"}), 401
    else:
        return jsonify({"error": "unauthorized"}), 401

    # Build a stable, non-sensitive demo key
    secret = os.getenv("SECRET_KEY", "dev-secret-key").encode("utf-8")
    digest = hmac.new(secret, email.encode("utf-8"), hashlib.sha256).hexdigest()[:24]
    # Looks like a key, but is worthless outside this demo
    demo_key = f"brikk_{digest}"

    return jsonify({"key": demo_key}), 200
