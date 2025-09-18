# src/routes/billing.py
import os
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request_optional

billing_bp = Blueprint("billing", __name__)

def _stripe():
    """Initialize Stripe if STRIPE_SECRET is present; else return None."""
    sk = (os.getenv("STRIPE_SECRET") or "").strip()
    if not sk:
        return None
    import stripe  # lazy import so app can boot without stripe installed
    stripe.api_key = sk
    return stripe

def _guess_email():
    """Try JWT first, then body.email."""
    try:
        verify_jwt_in_request_optional()
        ident = get_jwt_identity()
        if isinstance(ident, str) and "@" in ident:
            return ident.lower()
        if isinstance(ident, dict) and ident.get("email"):
            return str(ident["email"]).lower()
    except Exception:
        pass
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    return email or None

@billing_bp.route("/billing/portal", methods=["POST"])
def billing_portal():
    s = _stripe()
    if not s:
        return jsonify({"error": "Stripe not configured"}), 501

    email = _guess_email()
    if not email:
        return jsonify({"error": "missing email"}), 400

    # Find or create a Customer by email
    try:
        matches = s.Customer.list(email=email, limit=1).data  # type: ignore[attr-defined]
        if matches:
            customer_id = matches[0].id
        else:
            customer_id = s.Customer.create(email=email).id     # type: ignore[attr-defined]
    except Exception as e:
        return jsonify({"error": f"stripe customer error: {e}"}), 502

    return_url = os.getenv("BILLING_PORTAL_RETURN_URL", "https://www.getbrikk.com/app/")

    try:
        session = s.billing_portal.Session.create(              # type: ignore[attr-defined]
            customer=customer_id,
            return_url=return_url,
        )
        return jsonify({"url": session.url}), 200
    except Exception as e:
        return jsonify({"error": f"portal error: {e}"}), 502
