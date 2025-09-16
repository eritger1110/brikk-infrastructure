# src/routes/auth.py
import os, json
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, redirect
from flask_jwt_extended import (
    create_access_token,
    set_access_cookies,
    unset_jwt_cookies,
    jwt_required,
    get_jwt_identity,
)

from src.database.db import db
from src.models.user import User
from src.services.emailer import send_email

# NOTE: only "/auth" here; main.py mounts blueprint at "/api"
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

APP_BASE = os.environ.get("APP_BASE_URL", "https://app.getbrikk.com")
PROVISION_SECRET = os.environ.get("PROVISION_SECRET", "")  # set in Render env or leave blank to bypass token check


def _json_err(code: int, msg: str):
    return jsonify({"success": False, "error": msg}), code


def _loose_json():
    """
    Parse request body very defensively:
    - try JSON (even if content-type is wrong)
    - fall back to form fields
    - fall back to raw body json.loads
    """
    data = request.get_json(silent=True)
    if isinstance(data, dict) and data:
        return data

    if request.form:
        return dict(request.form)

    raw = (request.data or b"").decode("utf-8", "ignore").strip()
    if raw:
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    return {}


@auth_bp.route("/_debug-echo", methods=["POST", "OPTIONS"])
def debug_echo():
    data = _loose_json()
    return jsonify({
        "ok": True,
        "method": request.method,
        "json": data,
        "content_type": request.headers.get("Content-Type"),
        "origin": request.headers.get("Origin"),
    }), 200


@auth_bp.post("/complete-signup")
def complete_signup():
    """
    Body: { token, first_name, last_name, email, password }
    If PROVISION_SECRET is set, 'token' must match it.
    """
    data = _loose_json()

    token = (data.get("token") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()

    missing = []
    if not email: missing.append("email")
    if not password: missing.append("password")
    if PROVISION_SECRET and not token: missing.append("token")
    if missing:
        return _json_err(400, f"missing required field(s): {', '.join(missing)}")

    if PROVISION_SECRET and token != PROVISION_SECRET:
        return _json_err(403, "Invalid or expired token")

    # Create or update the user
    u = User.query.filter_by(email=email).first()
    if not u:
        username = (first or email.split("@", 1)[0] or "user").lower()
        u = User(username=username, email=email)

    if hasattr(u, "first_name"):
        u.first_name = first
    if hasattr(u, "last_name"):
        u.last_name = last

    u.set_password(password)
    if hasattr(u, "email_verified"):
        u.email_verified = True
    if hasattr(u, "clear_verification"):
        u.clear_verification()

    db.session.add(u)
    db.session.commit()

    # Log the user in via cookie
    access = create_access_token(identity=str(u.id))
    resp = jsonify({"success": True, "user": u.to_dict()})
    set_access_cookies(resp, access)
    return resp


@auth_bp.post("/register")
def register():
    data = _loose_json()
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not email or not password:
        return _json_err(400, "username, email, password are required")

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return _json_err(409, "User with that username or email already exists")

    u = User(username=username, email=email)
    u.set_password(password)
    if hasattr(u, "email_verified"):
        u.email_verified = False
    if hasattr(u, "issue_verification"):
        u.issue_verification(minutes=120)

    db.session.add(u)
    db.session.commit()

    if hasattr(u, "verification_token"):
        verify_link = f"{APP_BASE}/verify/?token={u.verification_token}"
        html = f"""
          <p>Welcome to Brikk!</p>
          <p>Please verify your email by clicking the link below:</p>
          <p><a href="{verify_link}">Verify my email</a></p>
          <p>This link expires in 2 hours.</p>
        """
        send_email(u.email, "Verify your Brikk email", html)

    return jsonify({"success": True, "message": "Check your email for a verification link"})


@auth_bp.get("/verify")
def verify():
    token = request.args.get("token", "")
    if not token:
        return _json_err(400, "Missing token")

    u = User.query.filter_by(verification_token=token).first()
    if not u:
        return _json_err(400, "Invalid or used token")

    if not getattr(u, "verification_expires", None) or datetime.now(timezone.utc) > u.verification_expires:
        return _json_err(400, "Token expired")

    if hasattr(u, "email_verified"):
        u.email_verified = True
    if hasattr(u, "clear_verification"):
        u.clear_verification()
    db.session.commit()

    access = create_access_token(identity=str(u.id))
    response = redirect(f"{APP_BASE}/app/")
    set_access_cookies(response, access)
    return response


@auth_bp.post("/login")
def login():
    data = _loose_json()
    user_or_email = (data.get("user_or_email") or "").strip()
    password = data.get("password") or ""

    if not user_or_email or not password:
        return _json_err(400, "user_or_email and password are required")

    u = User.query.filter(
        (User.email == user_or_email.lower()) | (User.username == user_or_email)
    ).first()

    if not u or not u.check_password(password):
        return _json_err(401, "Invalid credentials")

    if getattr(u, "email_verified", True) is False:
        return _json_err(403, "Email not verified")

    access = create_access_token(identity=str(u.id))
    resp = jsonify({"success": True, "user": u.to_dict()})
    set_access_cookies(resp, access)
    return resp


@auth_bp.post("/logout")
def logout():
    resp = jsonify({"success": True})
    unset_jwt_cookies(resp)
    return resp


@auth_bp.get("/me")
@jwt_required()
def me():
    uid = get_jwt_identity()
    u = User.query.get(int(uid))
    if not u:
        return _json_err(404, "User not found")
    return jsonify({"success": True, "user": u.to_dict()})


@auth_bp.post("/resend")
def resend():
    data = _loose_json()
    email = (data.get("email") or "").lower().strip()
    if not email:
        return _json_err(400, "email required")

    u = User.query.filter_by(email=email).first()
    if not u:
        return _json_err(404, "No user with that email")
    if getattr(u, "email_verified", False):
        return _json_err(400, "Email already verified")

    if hasattr(u, "issue_verification"):
        u.issue_verification(120)
    db.session.commit()

    if hasattr(u, "verification_token"):
        verify_link = f"{APP_BASE}/verify/?token={u.verification_token}"
        send_email(u.email, "Verify your Brikk email", f'<p>Verify: <a href="{verify_link}">{verify_link}</a></p>')

    return jsonify({"success": True, "message": "Verification email sent"})
