# src/routes/security.py
import os
import re
import secrets
import datetime as dt
from flask import Blueprint, request, jsonify, current_app, redirect, make_response
from flask_jwt_extended import create_access_token, set_access_cookies
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import jwt as pyjwt
import bcrypt

from src.models.user import User, db
from src.models.purchase import Purchase  # <-- new model (below)

security_bp = Blueprint("security", __name__)

PROVISION_SECRET   = os.environ.get("PROVISION_SECRET")
JWT_COOKIE_DOMAIN  = os.environ.get("COOKIE_DOMAIN")           # e.g. ".getbrikk.com"
FROM_EMAIL         = os.environ.get("FROM_EMAIL")              # e.g. "support@getbrikk.com"
SENDGRID_KEY       = os.environ.get("SENDGRID_API_KEY")
APP_URL            = os.environ.get("APP_URL", "https://www.getbrikk.com")
APP_DASHBOARD_PATH = os.environ.get("APP_DASHBOARD_PATH", "/app")  # where the app lives

# -------------------------------
# Helpers
# -------------------------------
ALNUM = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no confusing chars
def gen_order_ref(n: int = 10) -> str:
    return "BRK-" + "".join(secrets.choice(ALNUM) for _ in range(n))

def unique_order_ref(n: int = 10) -> str:
    # ensure uniqueness in DB (very low chance of collision, but be safe)
    for _ in range(5):
        ref = gen_order_ref(n)
        if not Purchase.query.filter_by(order_ref=ref).first():
            return ref
    # extremely unlikely to get here
    return gen_order_ref(n + 2)

def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def _set_password(user: User, pw: str):
    # Try common patterns. Adjust to your model if needed.
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
    link = f"{APP_URL.rstrip('/')}/verify?token={vtoken}"
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
    # Issue JWT cookie and return a 200
    claims = {"email": getattr(user, "email", None)}
    if payload:
        claims.update(payload)
    access = create_access_token(identity=str(getattr(user, "id", getattr(user, "email", ""))), additional_claims=claims)
    resp = jsonify({"ok": True})
    set_access_cookies(resp, access)
    return resp

# -------------------------------
# POST /api/auth/complete-signup
# -------------------------------
@security_bp.route("/auth/complete-signup", methods=["POST"])
def complete_signup():
    """
    Body: { token, first_name, last_name, password }
    token is a short-lived JWT issued by the Netlify provision-link function (signed with PROVISION_SECRET).
    - Creates/updates User
    - Creates a Purchase row w/ unique order_ref (if not already present for this subscription)
    - Sends verification email
    - Logs the user in (JWT cookie)
    """
    try:
        data = request.get_json() or {}
        token = data.get("token")
        first = (data.get("first_name") or "").strip()
        last  = (data.get("last_name")  or "").strip()
        pw    = data.get("password")

        if not token: return jsonify({"error":"missing token"}), 400
        if not first or not last: return jsonify({"error":"missing name"}), 400
        if not pw: return jsonify({"error":"missing password"}), 400
        if not PROVISION_SECRET: return jsonify({"error":"server missing PROVISION_SECRET"}), 500

        payload = pyjwt.decode(token, PROVISION_SECRET, algorithms=["HS256"], issuer="brikk-netlify")
        email   = (payload.get("email") or "").strip().lower()
        customer_id     = payload.get("customer")      # may be None
        subscription_id = payload.get("subscription")  # may be None
        if not email:
            return jsonify({"error":"token missing email"}), 400

        # Create or update user
        user = User.query.filter_by(email=email).first()
        if not user:
            username = f"{first} {last}".strip()
            user = User(username=username, email=email)
            db.session.add(user)

        _set_password(user, pw)

        # Ensure verification fields exist and set
        vtoken = secrets.token_urlsafe(32)
        expires = dt.datetime.utcnow() + dt.timedelta(hours=24)
        if hasattr(user, "verification_token"):
            user.verification_token = vtoken
        if hasattr(user, "verification_expires_at"):
            user.verification_expires_at = expires
        if hasattr(user, "email_verified"):
            user.email_verified = False

        # Create (or find) a Purchase record to hold order_ref
        purchase = None
        if subscription_id:
            purchase = Purchase.query.filter_by(stripe_subscription_id=subscription_id).first()
        if not purchase:
            purchase = Purchase(
                order_ref=unique_order_ref(10),
                email=email,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
            )
            db.session.add(purchase)

        db.session.commit()

        # Send verification
        _send_verification(email, vtoken, first_name=first, order_ref=purchase.order_ref if purchase else None)

        # Login (JWT cookie) so /app opens immediately; they’ll still need to verify for “verified-only” features
        return _login_response(user, payload={"order_ref": getattr(purchase, "order_ref", None)})

    except pyjwt.ExpiredSignatureError:
        return jsonify({"error":"session link expired, please refresh the success page"}), 400
    except Exception as e:
        current_app.logger.exception("complete-signup failed")
        return jsonify({"error": str(e)}), 500

# -------------------------------
# GET /api/auth/verify
# -------------------------------
@security_bp.route("/auth/verify", methods=["GET"])
def verify_email():
    """
    Link from the verification email:  /verify?token=...
    - Marks the user as verified if token is valid & not expired
    - Logs in via JWT cookie
    - Redirects to /app
    """
    token = request.args.get("token", "").strip()
    if not token:
        return _simple_page("Verification", "<p>Missing token.</p>"), 400

    try:
        # Look up the user by verification token
        user = User.query.filter_by(verification_token=token).first()
        if not user:
            return _simple_page("Verification", "<p>Invalid verification link.</p>"), 400

        # Optional expiry check if your model has it
        if hasattr(user, "verification_expires_at") and user.verification_expires_at:
            if dt.datetime.utcnow() > user.verification_expires_at:
                return _simple_page("Verification", "<p>This verification link has expired.</p>"), 400

        # Mark verified (if your model has the field)
        if hasattr(user, "email_verified"):
            user.email_verified = True
        if hasattr(user, "verification_token"):
            user.verification_token = None
        if hasattr(user, "verification_expires_at"):
            user.verification_expires_at = None

        db.session.commit()

        # Log them in and redirect to app
        resp = redirect(APP_URL.rstrip("/") + APP_DASHBOARD_PATH)
        access = create_access_token(identity=str(getattr(user, "id", getattr(user, "email", ""))),
                                     additional_claims={"email": getattr(user, "email", None)})
        set_access_cookies(resp, access)
        return resp

    except Exception as e:
        current_app.logger.exception("verify failed")
        return _simple_page("Verification", f"<p>Something went wrong: {e}</p>"), 500

def _simple_page(title: str, body_html: str):
    html = f"""<!doctype html><meta charset="utf-8">
    <title>{title} – Brikk</title>
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
# POST /api/auth/resend-verification  (optional nicety)
# -------------------------------
@security_bp.route("/auth/resend-verification", methods=["POST"])
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
    if hasattr(user, "verification_token"):
        user.verification_token = vtoken
    if hasattr(user, "verification_expires_at"):
        user.verification_expires_at = expires
    db.session.commit()

    first = ""
    if hasattr(user, "username") and user.username:
        first = user.username.split(" ")[0]
    _send_verification(email, vtoken, first_name=first)
    return jsonify({"ok": True})
