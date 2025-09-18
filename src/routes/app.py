# src/routes/app.py
import os
from flask import Blueprint, jsonify, request

# Optional JWT (protect if desired)
try:
    from flask_jwt_extended import jwt_required, get_jwt_identity  # type: ignore
    HAVE_JWT = True
except Exception:
    HAVE_JWT = False

# Optional Stripe
try:
    import stripe  # type: ignore
    HAVE_STRIPE = True
except Exception:
    stripe = None
    HAVE_STRIPE = False

app_bp = Blueprint("app", __name__)

# --- Metrics (used by dashboard graphs) ---
@app_bp.route("/metrics", methods=["GET"])
def metrics():
    # Return a harmless empty dataset for now
    return jsonify({
        "requests": [],     # e.g., [{ts: "...", count: 0}]
        "latency_ms": [],   # e.g., [{ts: "...", p50: 0, p95: 0}]
    }), 200

# --- Run demo workflow (stub) ---
@app_bp.route("/workflows/<string:slug>/execute", methods=["POST","OPTIONS"])
def run_workflow(slug: str):
    if request.method == "OPTIONS": return ("", 204)
    inp = request.get_json(silent=True) or {}
    actor = None
    if HAVE_JWT:
        try:
            # optional; won't fail if no cookie
            from flask_jwt_extended import verify_jwt_in_request
            verify_jwt_in_request(optional=True)
            actor = get_jwt_identity()
        except Exception:
            actor = None
    return jsonify({
        "ok": True,
        "workflow": slug,
        "ran_as": actor,
        "echo": inp,
        "result": f"demo result for '{slug}'",
    }), 200

# --- Stripe Billing Portal (server-side) ---
@app_bp.route("/billing/portal", methods=["POST","OPTIONS"])
def billing_portal():
    if request.method == "OPTIONS": return ("", 204)
    secret = os.getenv("STRIPE_SECRET", "").strip()
    if not (HAVE_STRIPE and secret):
        return jsonify({"error": "Stripe not configured"}), 501

    stripe.api_key = secret

    # Use JWT email if available; otherwise allow client to pass {email:"..."}
    email = None
    if HAVE_JWT:
        try:
            from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
            verify_jwt_in_request(optional=True)
            ident = get_jwt_identity()
            if isinstance(ident, str) and "@" in ident: email = ident
        except Exception:
            email = None
    if not email:
        email = (request.get_json(silent=True) or {}).get("email")

    if not email:
        return jsonify({"error": "email required"}), 400

    # Try to find Stripe customer by email
    customer = None
    try:
        # Prefer search (faster/accurate) if enabled
        try:
            res = stripe.Customer.search(query=f'email:"{email}"', limit=1)
            if res and res.get("data"): customer = res["data"][0]
        except Exception:
            pass
        if not customer:
            res = stripe.Customer.list(email=email, limit=1)
            if res and res.get("data"): customer = res["data"][0]
    except Exception as e:
        return jsonify({"error": f"stripe error: {e}"}), 502

    if not customer:
        return jsonify({"error": "no customer for that email"}), 404

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer["id"],
            return_url=os.getenv("PORTAL_RETURN_URL", "https://www.getbrikk.com/app/"),
        )
        return jsonify({"url": session["url"]}), 200
    except Exception as e:
        return jsonify({"error": f"stripe portal error: {e}"}), 502
