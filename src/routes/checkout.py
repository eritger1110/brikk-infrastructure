"""
Stripe Checkout routes for subscription signup.
"""
import os
from flask import Blueprint, jsonify, request, current_app

try:
    import stripe
    HAVE_STRIPE = True
except Exception:
    HAVE_STRIPE = False

checkout_bp = Blueprint("checkout", __name__)


def _json():
    """Safely parse JSON body or return empty dict."""
    return (request.get_json(silent=True) or {}) if request.data else {}


@checkout_bp.route("/api/checkout/create-session", methods=["POST", "OPTIONS"])
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
        
        current_app.logger.info(f"[checkout] Created checkout session: {session.id}")
        return jsonify({"session_id": session.id}), 200

    except stripe.error.StripeError as e:
        msg = getattr(e, "user_message", None) or str(e)
        current_app.logger.error(f"Stripe error: {msg}")
        return jsonify({"error": f"Stripe error: {msg}"}), 502
    except Exception:
        current_app.logger.exception("Unexpected error creating checkout session")
        return jsonify({"error": "Unexpected server error"}), 500

