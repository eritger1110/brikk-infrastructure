# src/routes/security.py
import os
import secrets
import datetime as dt
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, set_access_cookies
from src.models.user import User, db  # adjust if your model path differs
import jwt as pyjwt
import bcrypt
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

security_bp = Blueprint("security", __name__)

PROVISION_SECRET = os.environ.get("PROVISION_SECRET")
JWT_COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN")  # optional e.g. ".getbrikk.com"
FROM_EMAIL = os.environ.get("FROM_EMAIL")  # e.g. support@getbrikk.com
APP_URL = os.environ.get("APP_URL", "https://www.getbrikk.com")  # where /app lives

def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def _set_password(user: User, pw: str):
    # Try common attributes/methods without knowing your exact model
    if hasattr(user, "set_password"):
        user.set_password(pw)
    elif hasattr(user, "password_hash"):
        user.password_hash = _hash_password(pw)
    elif hasattr(user, "password"):
        user.password = _hash_password(pw)
    else:
        raise RuntimeError("User model has no password field/method")

def _send_verification(email: str, vtoken: str, first_name: str = ""):
    if not FROM_EMAIL or not os.environ.get("SENDGRID_API_KEY"):
        current_app.logger.warning("SendGrid not configured; skipping email")
        return
    link = f"{APP_URL.rstrip('/')}/verify?token={vtoken}"
    subject = "Verify your email for Brikk"
    plain = f"Hi {first_name or ''}\n\nPlease verify your email by clicking this link:\n{link}\n\nThis link is valid for 24 hours."
    html = f"""
      <p>Hi {first_name or ''},</p>
      <p>Please verify your email by clicking this link:</p>
      <p><a href="{link}">Verify my email</a></p>
      <p>This link is valid for 24 hours.</p>
    """
    message = Mail(from_email=FROM_EMAIL, to_emails=email, subject=subject, plain_text_content=plain, html_content=html)
    sg = SendGridAPIClient(os.environ["SENDGRID_API_KEY"])
    sg.send(message)

@security_bp.route("/auth/complete-signup", methods=["POST"])
def complete_signup():
    """
    Body: { token, first_name, last_name, password }
    token is from Netlify provision-link (signed with PROVISION_SECRET)
    """
    try:
        data = request.get_json() or {}
        token = data.get("token")
        first = (data.get("first_name") or "").strip()
        last = (data.get("last_name") or "").strip()
        pw = data.get("password")

        if not token: return jsonify({"error":"missing token"}), 400
        if not first or not last: return jsonify({"error":"missing name"}), 400
        if not pw: return jsonify({"error":"missing password"}), 400
        if not PROVISION_SECRET: return jsonify({"error":"server missing PROVISION_SECRET"}), 500

        payload = pyjwt.decode(token, PROVISION_SECRET, algorithms=["HS256"], issuer="brikk-netlify")
        email = (payload.get("email") or "").strip().lower()
        if not email:
            return jsonify({"error":"token missing email"}), 400

        # find or create user
        user = User.query.filter_by(email=email).first()
        if not user:
            username = f"{first} {last}".strip()
            user = User(username=username, email=email)
            db.session.add(user)

        _set_password(user, pw)

        # simple verification token good for 24h
        vtoken = secrets.token_urlsafe(32)
        if hasattr(user, "verification_token"):
            user.verification_token = vtoken
        if hasattr(user, "verification_expires_at"):
            user.verification_expires_at = dt.datetime.utcnow() + dt.timedelta(hours=24)
        if hasattr(user, "email_verified"):
            user.email_verified = False

        db.session.commit()

        # email verification
        _send_verification(email, vtoken, first)

        # login cookie
        additional_claims = {"email": email}
        access = create_access_token(identity=str(getattr(user, "id", email)), additional_claims=additional_claims)
        resp = jsonify({"ok": True})
        set_access_cookies(resp, access)

        # add cookie domain if configured
        if JWT_COOKIE_DOMAIN:
            # flask-jwt-extended already sets cookies honoring app config; if needed, you can re-set here.
            pass

        return resp
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error":"session link expired, please refresh the success page"}), 400
    except Exception as e:
        current_app.logger.exception("complete-signup failed")
        return jsonify({"error": str(e)}), 500
