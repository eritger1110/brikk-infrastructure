# src/routes/welcome.py
import os
import jwt  # PyJWT
from flask import Blueprint, request, redirect, make_response
from flask_jwt_extended import create_access_token, set_access_cookies

welcome_bp = Blueprint("welcome_bp", __name__)

# --- Optional: light-touch user creation/upsert helpers ----------------------
def upsert_user(email, name=None, stripe_customer=None, stripe_subscription=None):
    """
    Replace this with your real model code. This is deliberately tolerant:
    - If your models aren't available yet, it won't crash the login step.
    - It only *tries* to update/insert.
    """
    try:
        # Example import — adjust to your actual model names:
        from src.models.customer_profile import db as _db, CustomerProfile  # type: ignore

        user = _db.session.query(CustomerProfile).filter_by(email=email).first()
        if not user:
            user = CustomerProfile(email=email, full_name=name or "", stripe_customer_id=stripe_customer or "")
            if hasattr(user, "stripe_subscription_id"):
                user.stripe_subscription_id = stripe_subscription or ""
            _db.session.add(user)
        else:
            if name and hasattr(user, "full_name"):
                user.full_name = name
            if stripe_customer and hasattr(user, "stripe_customer_id"):
                user.stripe_customer_id = stripe_customer
            if stripe_subscription and hasattr(user, "stripe_subscription_id"):
                user.stripe_subscription_id = stripe_subscription
        _db.session.commit()
        # Return a unique identity you use for JWTs. Commonly user.id.
        return getattr(user, "id", email)
    except Exception as e:
        # Fallback: just use email as identity if DB ops aren't wired yet
        return email
# ---------------------------------------------------------------------------


@welcome_bp.route("/welcome", methods=["GET"])
def welcome():
    """
    Accepts a short-lived provisioning token, creates/updates the user,
    sets the app auth cookie, and redirects to the app dashboard.
    """
    token = request.args.get("token", "")
    if not token:
        return "Missing token", 400

    secret = os.environ.get("PROVISION_SECRET")
    if not secret:
        return "Server misconfigured (no PROVISION_SECRET)", 500

    try:
        data = jwt.decode(token, secret, algorithms=["HS256"], issuer="brikk-netlify")
    except jwt.InvalidTokenError as e:
        return f"Invalid token: {e}", 400

    email = data.get("email")
    name = data.get("name")
    stripe_customer = data.get("customer")
    stripe_subscription = data.get("subscription")

    if not email and not stripe_customer:
        return "Invalid token payload", 400

    # Create or update your user record; get identity for JWT
    identity = upsert_user(email or stripe_customer, name, stripe_customer, stripe_subscription)

    # Issue your normal app JWT and set it as an HttpOnly cookie
    access = create_access_token(identity=identity, additional_claims={
        "email": email, "customer": stripe_customer, "subscription": stripe_subscription
    })
    resp = make_response(redirect("/"))   # <- change to '/dashboard' if you have one
    set_access_cookies(resp, access)
    return resp
