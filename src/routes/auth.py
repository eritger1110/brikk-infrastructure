# src/routes/auth.py
import os
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
PROVISION_SECRET = os.environ.get("PROVISION_SECRET", "")  # keep empty while testing, or set to a known value


def _json_err(code: int, msg: str):
    return jsonify({"success": False, "error": msg}), code


def _take_first_nonempty(*vals):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and v.strip() == "":
            continue
        return v
    return None


def _parse_body():
    """
    Tolerant body parser: JSON, then form, then querystring.
    Returns a dict with possible keys: token, email, password, first_name, last_name
    """
    data = {}
    if request.is_json:
        data = (request.get_json(silent=True) or {})  # JSON
    else:
        data = (request.get_json(silent=True) or {})  # try JSON anyway

    # fall back to form-encoded if present
    if not data and request.form:
        data = request.form.to_dict(flat=True)

    # make sure we don't miss values if they arrived via query
    for k in ("token", "email", "password", "first_name", "last_name"):
        data[k] = _take_first_nonempty(data.get(k), request.args.get(k))

    # normalize
    if "email" in data and isinstance(data["email"], str):
        data["email"] = data["email"].strip().lower()
    for k in ("first_name", "last_name", "token"):
        if k in data and isinstance(data[k], str):
            data[k] = data[k].strip()

    return data


# ---------------------------------------------------------------------
# Debug endpoint: echo back the payload. Useful for testing preflight + POST.
# ---------------------------------------------------------------------
@auth_bp.route("/_debug-echo", methods=["POST", "OPTIONS"])
def debug_echo():
    return jsonify({
        "ok": True,
        "json": _parse_body(),
        "headers": {k: v for k, v in request.headers.items()},
        "method": request.method,
    })


# ---------------------------------------------------------------------
# Success-page flow: create account and sign-in via cookie
# ---------------------------------------------------------------------
@auth_bp.post("/complete-signup")
def complete_signup():
    """
    Body (JSON or form): { token, first_name, last_name, email, password }
    If PROVISION_SECRET is set, token must match.
    """
    data = _parse_body()
    token = data.get("token")
    email = data.get("email")
    password = data.get("password")
    first = data.get("first_name") or ""
    last = data.get("last_name") or ""

    missing = [k for k in ("email", "password") if not data.get(k)]
    if PROVISION_SECRET and token != PROVISION_SECRET:
        return _json_err(403, "invalid token")
    if missing:
        return _json_err(400, f"missing required field(s): {', '.join(missing)}")

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

    access = create_access_token(identity=str(u.id))
    resp = jsonify({"success": True, "user": u.to_dict()})
    set_access_cookies(resp, access)
    return resp


@auth_bp.post("/register")
def register():
    data = _parse_body()
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
    data = _parse_body()
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
    data = _parse_body()
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
