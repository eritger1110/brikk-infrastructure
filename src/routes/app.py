# src/routes/app.py
import os
from typing import Dict, Any

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

# Stripe is optional. We return a 501 if it's not configured.
try:
    import stripe  # type: ignore
except Exception:  # pragma: no cover
    stripe = None  # type: ignore

app_bp = Blueprint("app", __name__)  # this is what main.py registers at url_prefix="/api"


# ---- Utilities --------------------------------------------------------------

def _ok(data: Dict[str, Any], status: int = 200):
    return jsonify(data), status


def _err(message: str, status: int):
    return jsonify({"error": message}), status


# ---- Debug: list all /api routes we have registered ------------------------

@app_bp.get("/_routes")
def all_routes():
    routes = []
    for rule in current_app.url_map.iter_rules():
        if rule.rule.startswith("/api/"):
            methods = sorted(list(rule.methods - {"HEAD", "OPTIONS"}))
            routes.append({"rule": rule.rule, "methods": methods, "endpoint": rule.endpoint})
    routes.sort(key=lambda r: r["rule"])
    return _ok({"count": len(routes), "routes": routes})


# ---- Simple dashboard metrics (stub) ---------------------------------------

@app_bp.get("/metrics")
def metrics():
    # Stubbed series so the charts have data; replace with real metrics later.
    series = {
        "last10m":  [2, 3, 5, 4, 6, 7, 4, 6, 5, 8],
        "latency":  [220, 210, 230, 190, 200, 240, 210, 220, 205, 215],
    }
    return _ok({"series": series})


# ---- Demo workflow executor (stub) -----------------------------------------

@app_bp.post("/workflows/<workflow>/execute")
@jwt_required(optional=True)
def execute_workflow(workflow: str):
    """
    Minimal echo so the dashboard has something to show.
    Replace with your actual workflow runner.
    """
    body = request.get_json(silent=True) or {}
    identity = get_jwt_identity()
    ran_as = None
    if isinstance(identity, dict):
        ran_as = identity.get("email") or identity.get("id")
    elif isinstance(identity, str):
        ran_as = identity

    result = {
        "ok": True,
        "workflow": workflow,
        "ran_as": ran_as,
        "echo": body.get("echo") or {"demo": True},
        "result": f"demo result for '{workflow}'",
    }
    return _ok(result)


# ---- Billing portal (Stripe) -----------------------------------------------

@app_bp.post("/billing/portal")
@jwt_required(optional=True)
def billing_portal():
    """
    Creates a Stripe Billing Portal session for the authenticated user.
    Requirements to return a URL:
      - STRIPE_SECRET_KEY env var is set
      - A Stripe Customer ID is known for this user (you need to implement lookup)
    """
    # 1) Require Stripe be configured
    secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret or stripe is None:
        return _err("Stripe not configured", 501)

    stripe.api_key = secret

    # 2) Determine which customer to open the portal for
    #    For now we try to infer from JWT identity or request JSON.
    identity = get_jwt_identity()
    email_from_jwt = None
    if isinstance(identity, dict):
        email_from_jwt = (identity.get("email") or "").strip().lower()
    elif isinstance(identity, str):
        # if you store plain email as identity
        email_from_jwt = identity.strip().lower()

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or email_from_jwt or "").strip().lower()

    # TODO: implement your mapping from user/email -> Stripe customer id.
    # For now, if you don’t have one, return a clear 400 so the UI can react.
    customer_id = data.get("customer_id")  # allow passing directly for testing

    if not customer_id:
        return _err("No Stripe customer on file for this user", 400)

    # 3) Create the portal session
    return_url = os.getenv("BILLING_PORTAL_RETURN_URL", "https://www.getbrikk.com/app/")
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return _ok({"url": session.url})
    except Exception as e:  # pragma: no cover
        current_app.logger.exception("Failed to create billing portal session")
        return _err(f"Stripe error: {str(e)}", 502)
