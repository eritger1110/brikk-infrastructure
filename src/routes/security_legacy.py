# src/routes/security.py
import os
import secrets
import datetime as dt
from flask import Blueprint, request, jsonify, current_app, redirect, make_response
from flask_jwt_extended import (
    create_access_token, set_access_cookies, unset_jwt_cookies,
    jwt_required, get_jwt_identity
)
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import jwt as pyjwt
import bcrypt

# '... Always import the shared db from database module
from src.database.db import db
from src.models.user import User
from src.models.purchase import Purchase

security_bp = Blueprint("security", __name__, url_prefix="/api")

# -------------------------------
# Environment
# -------------------------------
PROVISION_SECRET   = os.environ.get("PROVISION_SECRET")
JWT_COOKIE_DOMAIN  = os.environ.get("COOKIE_DOMAIN")                # e.g. ".getbrikk.com"
FROM_EMAIL         = os.environ.get("FROM_EMAIL")                   # e.g. "support@getbrikk.com"
SENDGRID_KEY       = os.environ.get("SENDGRID_API_KEY")
APP_URL            = os.environ.get("APP_URL", "https://www.getbrikk.com").rstrip("/")
APP_DASHBOARD_PATH = os.environ.get("APP_DASHBOARD_PATH", "/app")

# -------------------------------
# Helpers
# -------------------------------
ALNUM = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no confusing chars

def gen_order_ref(n: int = 10) -> str:
    return "BRK-" + "".join(secrets.choice(ALNUM) for _ in range(n))

def unique_order_ref(n: int = 10) -> str:
    for _ in range(5):
        ref = gen_order_ref(n)
        if not Purchase.query.filter_by(order_ref=ref).first():
            return ref
    return gen_order_ref(n + 2)

def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def _set_password(user: User, pw: str):
    if hasattr(user, "set_password"):
        user.set_password(pw)
    elif hasattr(user, "password_hash"):
        user.password_hash = _hash_password(pw)
    elif hasattr(user, "password"):
        user.password = _hash_password(pw)
    else:
        raise RuntimeError("User model has no password field/method")

def _send_verification(email: str, vtoken: str, first_name: str = "", order_ref: str | None = None):
    if not FROM_EMAIL or not SENDGRID_KEY:
        current_app.logger.warning("SendGrid not configured; skipping verification email")
        return
    link = f"{APP_URL}/verify?token={vtoken}"
    subject = "Verify your email for Brikk"
    plain = (
        f"Hi {first_name or ''}\n\n"
        f"Thanks for subscribing to Brikk."
        f"{f' Your order reference is {order_ref}.' if order_ref else ''}\n\n"
        f"Please verify your email by clicking this link:\n{link}\n\n"
        "This link is valid for 24 hours."
    )
    html = f"""
      <p>Hi {first_name or ''},</p>
      <p>Thanks for subscribing to Brikk.{f' Your order reference is <strong>{order_ref}</strong>.' if order_ref else ''}</p>
      <p>Please verify your email by clicking this link:</p>
      <p><a href="{link}">Verify my email</a></p>
      <p>This link is valid for 24 hours.</p>
    """
    message = Mail(from_email=FROM_EMAIL, to_emails=email, subject=subject, plain_text_content=plain, html_content=html)
    SendGridAPIClient(SENDGRID_KEY).send(message)

def _login_response(user: User, payload: dict | None = None):
    claims = {"email": getattr(user, "email", None)}
    if payload:
        claims.update(payload)
    identity = str(getattr(user, "id", getattr(user, "email", "")))
    access = create_access_token(identity=identity, additional_claims=claims)
    resp = jsonify({"ok": True, "user": {"id": identity, "email": getattr(user, "email", None)}})
    set_access_cookies(resp, access)
    return resp

# --- verification field helpers (works with either verification_expires or _at) ---
def _set_verification_fields(user: User, token: str, expires: dt.datetime):
    if hasattr(user, "verification_token"):
        user.verification_token = token
    if hasattr(user, "verification_expires"):
        user.verification_expires = expires
    if hasattr(user, "verification_expires_at"):
        user.verification_expires_at = expires
    if hasattr(user, "email_verified"):
        user.email_verified = False

def _get_verification_expiry(user: User) -> dt.datetime | None:
    return getattr(user, "verification_expires", None) or getattr(user, "verification_expires_at", None)

def _clear_verification_fields(user: User):
    if hasattr(user, "verification_token"):
        user.verification_token = None
    if hasattr(user, "verification_expires"):
        user.verification_expires = None
    if hasattr(user, "verification_expires_at"):
        user.verification_expires_at = None

# -------------------------------
# POST /api/auth/complete-signup
# -------------------------------
@security_bp.post("/auth/complete-signup")
def complete_signup():
    """
    Body: { token, first_name, last_name, email, password }
    token is a short-lived JWT issued by the Netlify provision-link function (signed with PROVISION_SECRET).
    - Creates/updates User
    - Creates a Purchase row w/ unique order_ref (if not already present for this subscription)
    - Sends verification email
    - Logs the user in (JWT cookie)
    """
    try:
        data = request.get_json() or {}
        token = (data.get("token") or "").strip()
        first = (data.get("first_name") or "").strip()
        last  = (data.get("last_name")  or "").strip()
        email = (data.get("email")      or "").strip().lower()
        pw    = data.get("password")

        if not token: return jsonify({"error":"missing token"}), 400
        if not first or not last: return jsonify({"error":"missing name"}), 400
        if not email: return jsonify({"error":"missing email"}), 400
        if not pw: return jsonify({"error":"missing password"}), 400
        if not PROVISION_SECRET: return jsonify({"error":"server missing PROVISION_SECRET"}), 500

        payload = pyjwt.decode(token, PROVISION_SECRET, algorithms=["HS256"], issuer="brikk-netlify")
        token_email       = (payload.get("email") or "").strip().lower()
        customer_id       = payload.get("customer")
        subscription_id   = payload.get("subscription")
        effective_email   = token_email or email
        if not effective_email:
            return jsonify({"error":"token missing email"}), 400

        # Create or update user
        user = User.query.filter_by(email=effective_email).first()
        if not user:
            username = f"{first} {last}".strip()
            user = User(username=username, email=effective_email)
            db.session.add(user)

        _set_password(user, pw)

        # Set verification fields
        vtoken  = secrets.token_urlsafe(32)
        expires = dt.datetime.utcnow() + dt.timedelta(hours=24)
        _set_verification_fields(user, vtoken, expires)

        # Create/find purchase record for order_ref
        purchase = None
        if subscription_id:
            purchase = Purchase.query.filter_by(stripe_subscription_id=subscription_id).first()
        if not purchase:
            purchase = Purchase(
                order_ref=unique_order_ref(10),
                email=effective_email,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
            )
            db.session.add(purchase)

        db.session.commit()

        # Send verification
        _send_verification(effective_email, vtoken, first_name=first, order_ref=purchase.order_ref if purchase else None)

        # Login immediately
        return _login_response(user, payload={"order_ref": getattr(purchase, "order_ref", None)})

    except pyjwt.ExpiredSignatureError:
        return jsonify({"error":"session link expired, please refresh the success page"}), 400
    except Exception as e:
        current_app.logger.exception("complete-signup failed")
        return jsonify({"error": str(e)}), 500

# -------------------------------
# GET /api/auth/verify
# -------------------------------
@security_bp.get("/auth/verify")
def verify_email():
    token = request.args.get("token", "").strip()
    if not token:
        return _simple_page("Verification", "<p>Missing token.</p>"), 400
    try:
        user = User.query.filter_by(verification_token=token).first()
        if not user:
            return _simple_page("Verification", "<p>Invalid verification link.</p>"), 400

        exp = _get_verification_expiry(user)
        if exp and dt.datetime.utcnow() > exp:
            return _simple_page("Verification", "<p>This verification link has expired.</p>"), 400

        if hasattr(user, "email_verified"):
            user.email_verified = True
        _clear_verification_fields(user)

        db.session.commit()

        # Log them in and redirect to app
        resp = redirect(APP_URL + APP_DASHBOARD_PATH)
        identity = str(getattr(user, "id", getattr(user, "email", "")))
        access = create_access_token(identity=identity, additional_claims={"email": getattr(user, "email", None)})
        set_access_cookies(resp, access)
        return resp

    except Exception as e:
        current_app.logger.exception("verify failed")
        return _simple_page("Verification", f"<p>Something went wrong: {e}</p>"), 500

def _simple_page(title: str, body_html: str):
    html = f"""<!doctype html><meta charset="utf-8">
    <title>{title} '" Brikk</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <body style="background:#0b0f1a;color:#e7ecff;font:16px/1.5 system-ui;margin:40px">
      <h1 style="margin:0 0 10px">{title}</h1>
      {body_html}
      <p style="margin-top:10px"><a href="{APP_URL}">Go to site</a></p>
    </body>"""
    r = make_response(html)
    r.headers["content-type"] = "text/html"
    return r

# -------------------------------
# POST /api/auth/resend-verification
# -------------------------------
@security_bp.post("/auth/resend-verification")
def resend_verification():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error":"missing email"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error":"no account for that email"}), 404
    if hasattr(user, "email_verified") and user.email_verified:
        return jsonify({"error":"email already verified"}), 400

    vtoken = secrets.token_urlsafe(32)
    expires = dt.datetime.utcnow() + dt.timedelta(hours=24)
    _set_verification_fields(user, vtoken, expires)
    db.session.commit()

    first = ""
    if hasattr(user, "username") and user.username:
        first = user.username.split(" ")[0]
    _send_verification(email, vtoken, first_name=first)
    return jsonify({"ok": True})

# -------------------------------
# GET /api/auth/me
# -------------------------------
@security_bp.get("/auth/me")
@jwt_required(optional=True)
def me():
    ident = get_jwt_identity()
    if not ident:
        return jsonify({"user": None}), 200

    user = User.query.filter((User.id == ident) | (User.email == ident)).first()
    if not user:
        return jsonify({"user": None}), 200

    # fetch latest order ref if present
    purchase = Purchase.query.filter_by(email=user.email).order_by(Purchase.id.desc()).first()
    return jsonify({
        "user": {
            "id": str(getattr(user, "id", "")),
            "email": getattr(user, "email", None),
            "username": getattr(user, "username", None),
            "email_verified": getattr(user, "email_verified", False)
        },
        "order_ref": getattr(purchase, "order_ref", None)
    })

# -------------------------------
# POST /api/auth/logout
# -------------------------------
@security_bp.post("/auth/logout")
def logout():
    resp = jsonify({"ok": True})
    unset_jwt_cookies(resp)
    return resp
