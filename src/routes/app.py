# src/routes/app.py
import os
from typing import Optional

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

# Stripe (12.x)
import stripe

app_bp = Blueprint("app", __name__)  # mounted under /api by main.py

# ---- helpers ---------------------------------------------------------------

def _stripe_ready() -> bool:
    api_key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    if not api_key:
        return False
    stripe.api_key = api_key
    return True

def _current_email() -> Optional[str]:
    """
    We store the user's email as the JWT identity during login/sign-up.
    If you encode a different identity, adjust this accordingly.
    """
    try:
        ident = get_jwt_identity()
        if isinstance(ident, str) and "@" in ident:
            return ident
        if isinstance(ident, dict):
            # common pattern: {"email": "...", ...}
            email = ident.get("email")
            if isinstance(email, str) and "@" in email:
                return email
    except Exception:
        pass
    return None

def _find_or_create_customer(email: str) -> stripe.Customer:
    """
    1) Try to find an existing Stripe customer by email.
    2) If none found, create a new one so the portal can open.
    NOTE: If your checkout flow definitely creates a customer, step (1) will hit.
    """
    # Search (fast path). If search isn’t enabled on your account, fallback below.
    try:
        res = stripe.Customer.search(query=f"email:'{email}'", limit=1)
        if res and res.data:
            return res.data[0]
    except Exception:
        # Some accounts don’t have Customer Search – fall back to list.
        existing = stripe.Customer.list(email=email, limit=1)
        if existing and existing.data:
            return existing.data[0]

    # Create a new customer so the portal can still open
    return stripe.Customer.create(email=email, metadata={"source": "brikk-dashboard"})

# ---- debug / discovery -----------------------------------------------------

@app_bp.get("/_routes")
def all_routes():
    # Handy to confirm what’s mounted at /api/*
    from flask import current_app
    out = []
    for rule in current_app.url_map.iter_rules():
        if rule.rule.startswith("/api/"):
            methods = sorted(list(rule.methods - {"HEAD", "OPTIONS"}))
            out.append({"endpoint": rule.endpoint, "methods": methods, "rule": rule.rule})
    return jsonify({"count": len(out), "routes": out})

# ---- metrics (stub so charts work) ----------------------------------------

@app_bp.get("/metrics")
def metrics():
    # Replace later with real data
    return jsonify({
        "series": {
            "last10m": [2, 3, 5, 4, 6, 7, 4, 6, 5, 8],
            "latency": [220, 210, 230, 190, 200, 240, 210, 220, 205, 215],
        }
    })

# ---- billing portal --------------------------------------------------------

@app_bp.post("/billing/portal")
@jwt_required(optional=False)
def billing_portal():
    if not _stripe_ready():
        return jsonify({"error": "Stripe not configured"}), 500

    email = _current_email()
    if not email:
        return jsonify({"error": "Not authenticated"}), 401

    try:
        customer = _find_or_create_customer(email)
        return_url = (os.getenv("BILLING_PORTAL_RETURN_URL") or "https://www.getbrikk.com/app/").strip()
        session = stripe.billing_portal.Session.create(
            customer=customer.id,
            return_url=return_url,
        )
        return jsonify({"url": session.url})
    except stripe.error.StripeError as e:
        # Bubble Stripe error message so you can see exactly what’s wrong
        return jsonify({"error": f"Stripe error: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---- demo workflows --------------------------------------------------------

@app_bp.post("/workflows/<workflow>/execute")
@jwt_required(optional=True)
def execute_workflow(workflow: str):
    """
    Demo handler that echoes back a pretend result so the dashboard
    looks alive. Swap this with real logic when ready.
    """
    email = _current_email() or "—"
    body = request.get_json(silent=True) or {}
    return jsonify({
        "ok": True,
        "workflow": workflow,
        "ran_as": email,
        "result": f"demo result for '{workflow}'",
        "echo": {"demo": True} if body is None else body,
    })
