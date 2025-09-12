from datetime import datetime, timedelta, timezone
import os
import re
import bcrypt
import jwt as pyjwt  # PyJWT
from flask import Blueprint, request, jsonify, current_app, make_response
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
)
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from src.models.agent import db
from src.models.user import User  # <- adjust if your model path/name differs

security_bp = Blueprint("security", __name__)

# ---------- helpers ----------

def password_is_strong(pw: str) -> tuple[bool, str]:
    if len(pw) < 10:
        return False, "Minimum length is 10 characters"
    if not re.search(r"[A-Z]", pw):
        return False, "Must include at least one uppercase letter"
    if not re.search(r"[a-z]", pw):
        return False, "Must include at least one lowercase letter"
    if not re.search(r"\d", pw):
        return False, "Must include at least one number"
    if not re.search(r"[^\w\s]", pw):
        return False, "Must include at least one symbol"
    return True, ""

def send_verification_email(to_email: str, token: str):
    api_key = os.environ.get("SENDGRID_API_KEY")
    from_email = os.environ.get("FROM_EMAIL", "no-reply@getbrikk.com")
    if not api_key:
        current_app.logger.warning("SENDGRID_API_KEY not set; skipping email.")
        return

    # Where should users click to verify? This can be Netlify (/verify) or any route you own.
    verify_link = f"https://www.getbrikk.com/verify/?token={token}"

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject="Verify your email for Brikk",
        html_content=f"""
        <p>Welcome to Brikk!</p>
        <p>Click the link below to verify your email address:</p>
        <p><a href="{verify_link}">{verify_link}</a></p>
        <p>This link expires in 24 hours.</p>
        """
    )
    try:
        sg = SendGridAPIClient(api_key)
        sg.send(message)
    except Exception as e:
        current_app.logger.exception("Failed to send verification email: %s", e)

def make_email_token(email: str) -> str:
    secret = current_app.config["JWT_SECRET_KEY"]
    payload = {
        "sub": email,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()),
        "type": "email-verify",
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")

def decode_email_token(token: str) -> str | None:
    try:
        payload = pyjwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
        if payload.get("type") != "email-verify":
            return None
        return payload.get("sub")
    except Exception:
        return None

# ---------- routes ----------

@security_bp.post("/api/signup")
def signup():
    data = request.get_json(silent=True) or {}
    first = (data.get("first_name") or "").strip()
    last  = (data.get("last_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    pw    = data.get("password") or ""
    confirm = data.get("confirm_password") or ""

    if not first or not last or not email or not pw:
        return jsonify({"error": "All fields are required"}), 400
    if pw != confirm:
        return jsonify({"error": "Passwords do not match"}), 400

    ok, why = password_is_strong(pw)
    if not ok:
        return jsonify({"error": why}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "An account with this email already exists"}), 409

    pw_hash = bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    user = User(
        # adjust field names if your model differs
        email=email,
        first_name=first,
        last_name=last,
        password_hash=pw_hash,
        is_verified=False,
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(user)
    db.session.commit()

    # send verification email (non-blocking best-effort)
    token = make_email_token(email)
    send_verification_email(email, token)

    # sign them in right away so they land in dashboard
    access = create_access_token(identity=email)
    resp = make_response(jsonify({"status": "ok"}))
    set_access_cookies(resp, access)
    return resp

@security_bp.get("/api/verify")
def verify_email():
    token = request.args.get("token", "")
    email = decode_email_token(token)
    if not email:
        return jsonify({"error": "Invalid or expired token"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Account not found"}), 404

    user.is_verified = True
    db.session.commit()
    return jsonify({"status": "verified"})

@security_bp.get("/api/me")
@jwt_required(optional=True)
def me():
    ident = get_jwt_identity()
    if not ident:
        return jsonify({"authenticated": False}), 200
    user = User.query.filter_by(email=ident).first()
    if not user:
        return jsonify({"authenticated": False}), 200
    return jsonify({
        "authenticated": True,
        "email": user.email,
        "name": f"{user.first_name} {user.last_name}".strip(),
        "verified": bool(getattr(user, "is_verified", False)),
        "plan": "pro",
    })

@security_bp.post("/api/logout")
def logout():
    resp = make_response(jsonify({"status": "ok"}))
    unset_jwt_cookies(resp)
    return resp
