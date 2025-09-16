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

# NOTE: only "/auth" here; main.py mounts at "/api"
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

APP_BASE = os.environ.get("APP_BASE_URL", "https://app.getbrikk.com")
PROVISION_SECRET = os.environ.get("PROVISION_SECRET", "")  # e.g. "debug"

def _err(code, msg):
    return jsonify({"success": False, "error": msg}), code

# ---- debug helpers -------------------------------------------------

@auth_bp.get("/_ping")
def ping():
    return jsonify({
        "success": True,
        "message": "pong",
        "provision_secret_set": bool(PROVISION_SECRET),
    })

@auth_bp.route("/_debug-echo", methods=["GET", "POST"])
def debug_echo():
    body = request.get_json(silent=True) or {}
    return jsonify({
        "success": True,
        "method": request.method,
        "json_ok": isinstance(body, dict),
        "json": body,
    })

# ---- primary flows -------------------------------------------------

@auth_bp.post("/complete-signup")
def complete_signup():
    """
    Body: { token, first_name, last_name, email, password }
    If PROVISION_SECRET is set, token must equal PROVISION_SECRET.
    """
    data = request.get_json(silent=True) or {}

    token     = (data.get("token") or "").strip()
    email     = (data.get("email") or "").strip().lower()
    password  = data.get("password") or ""
    first     = (data.get("first_name") or "").strip()
    last      = (data.get("last_name") or "").strip()

    if not email:
        return _err(400, "missing email")
    if not password:
        return _err(400, "missing password")

    if PROVISION_SECRET and token != PROVISION_SECRET:
        return _err(403, "invalid token")

    u = User.query.filter_by(email=email).first()
    if not u:
        username = (first or email.split("@",1)[0] or "user").lower()
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
