# src/routes/app.py
from __future__ import annotations

import os
import hashlib
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request, current_app
from werkzeug.exceptions import BadRequest

# Optional JWT (for knowing who the user is)
try:
    from flask_jwt_extended import jwt_required, get_jwt_identity  # type: ignore
    HAVE_JWT = True
except Exception:  # pragma: no cover
    HAVE_JWT = False

# Stripe
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "").strip()

app_bp = Blueprint("app", __name__)  # mounted at /api in main.py


def _json() -> Dict[str, Any]:
    return (request.get_json(silent=True) or {}) if request.data else {}


# --------------------------------------------------------------------------- #
# Helper: find Stripe customer by email (uses Customers Search)
# --------------------------------------------------------------------------- #
def _find_customer_id_for_email(email: str) -> str | None:
    if not stripe.api_key:
        raise RuntimeError("Stripe not configured")
    # Stripe Customers Search requires live mode enabled on your account
    # and the API key to be valid. We use exact email match.
    try:
        res = stripe.Customer.search(query=f"email:'{email}'", limit=1)
        if res and res.data:
            return res.data[0]["id"]
        return None
    except Exception as e:  # bubble detailed error to logs, generic to client
        current_app.logger.exception("Stripe customer search failed: %s", e)
        raise


# --------------------------------------------------------------------------- #
# Diagnostics
# --------------------------------------------------------------------------- #
@app_bp.route("/_routes", methods=["GET"])
def all_routes():
    routes: List[Dict[str, Any]] = []
    for r in current_app.url_map.iter_rules():
        if str(r).startswith("/api"):
            routes.append(
                {
                    "rule": str(r),
                    "methods": sorted(list(r.methods - {"HEAD", "OPTIONS"})),
                    "endpoint": r.endpoint,
                }
            )
    return jsonify({"count": len(routes), "routes": routes})


# --------------------------------------------------------------------------- #
# Charts – simple demo series
# --------------------------------------------------------------------------- #
@app_bp.route("/metrics", methods=["GET"])
def metrics():
    # Static-ish demo data; replace later with real metrics
    return jsonify(
        {
            "series": {
                "last10m": [2, 3, 5, 4, 6, 7, 4, 6, 5, 8],
                "latency": [220, 210, 230, 190, 200, 240, 210, 220, 205, 215],
            }
        }
    )


# --------------------------------------------------------------------------- #
# Demo workflows
# --------------------------------------------------------------------------- #
@app_bp.route("/workflows/<workflow>/execute", methods=["POST", "OPTIONS"])
def execute_workflow(workflow: str):
    if request.method == "OPTIONS":
        return ("", 204)
    payload = _json()
    who = None
    if HAVE_JWT:
        try:
            who = get_jwt_identity()
        except Exception:
            who = None

    return jsonify(
        {
            "ok": True,
            "workflow": workflow,
            "ran_as": who,
            "echo": {"demo": True, **payload},
            "result": f"demo result for '{workflow}'",
        }
    )


# --------------------------------------------------------------------------- #
# Billing portal (Stripe)
# --------------------------------------------------------------------------- #
@app_bp.route("/billing/portal", methods=["POST", "OPTIONS"])
def billing_portal():
    if request.method == "OPTIONS":
        return ("", 204)

    if not stripe.api_key:
        return jsonify({"error": "Stripe not configured"}), 500

    return_url = os.getenv("BILLING_PORTAL_RETURN_URL", "").strip()
    if not return_url:
        return jsonify({"error": "BILLING_PORTAL_RETURN_URL not set"}), 500

    data = _json()
    customer_id = (data.get("customer_id") or "").strip()

    # If a specific customer_id is supplied, prefer it (useful for admin tools)
    if not customer_id:
        # Otherwise derive from the logged-in email
        email = None
        if HAVE_JWT:
            try:
                email = get_jwt_identity()
            except Exception:
                email = None
        if not email or "@" not in str(email):
            return jsonify({"error": "No Stripe customer on file for this user"}), 400

        try:
            cid = _find_customer_id_for_email(str(email))
        except Exception:
            # Already logged server-side
            return (
                jsonify(
                    {
                        "error": "Could not locate Stripe customer for this email. "
                        "Ensure the checkout used the same email."
                    }
                ),
                502,
            )
        if not cid:
            return jsonify({"error": "No Stripe customer on file for this user"}), 400
        customer_id = cid

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id, return_url=return_url
        )
        return jsonify({"url": session.url})
    except Exception as e:
        current_app.logger.exception("Stripe portal create failed: %s", e)
        return jsonify({"error": f"Stripe error: {str(e)}"}), 502


# --------------------------------------------------------------------------- #
# API key reveal (temporary demo)
# --------------------------------------------------------------------------- #
@app_bp.route("/key", methods=["GET"])
def api_key_demo():
    """
    Temporary/demo key until we add DB-backed keys.
    Generates a deterministic token from email + SECRET_KEY so the same user
    sees the same key across sessions, but nothing is persisted.
    """
    email = None
    if HAVE_JWT:
        try:
            email = get_jwt_identity()
        except Exception:
            email = None

    if not email or "@" not in str(email):
        return jsonify({"error": "Not authenticated"}), 401

    secret = os.getenv("SECRET_KEY", "brikk-demo")
    h = hashlib.sha256(f"{email}:{secret}".encode("utf-8")).hexdigest()[:24]
    demo_key = f"brk_live_{h}"
    return jsonify({"key": demo_key})
