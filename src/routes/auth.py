# src/routes/auth.py
import os
from datetime import datetime, timezone
from urllib.parse import urlencode

from flask import Blueprint, request, jsonify, redirect
from flask_jwt_extended import (
    create_access_token, set_access_cookies, unset_jwt_cookies,
    jwt_required, get_jwt_identity
)

# ✅ Use the shared SQLAlchemy instance from src.database.db
from src.database.db import db
# ✅ Import only the model from src.models.user (not db)
from src.models.user import User

from src.services.emailer import send_email

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

APP_BASE = os.environ.get("APP_BASE_URL", "https://app.getbrikk.com")
API_BASE = os.environ.get("API_BASE_URL", "https://api.getbrikk.com")

def _json_err(code, msg):
    return jsonify({"success": False, "error": msg}), code

@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not email or not password:
        return _json_err(400, "username, email, password are required")

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return _json_err(409, "User with that username or email already exists")

    u = User(username=username, email=email)
    u.set_password(password)
    u.email_verified = False
    u.issue_verification(minutes=120)

    db.session.add(u)
    db.session.commit()

    # send verification link
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

    if not u.verification_expires or datetime.now(timezone.utc) > u.verification_expires:
        return _json_err(400, "Token expired")

    u.email_verified = True
    u.clear_verification()
    db.session.commit()

    # Auto-issue session cookie and bounce to /app
    access = create_access_token(identity=str(u.id))
    response = redirect(f"{APP_BASE}/app/")
    set_access_cookies(response, access)
    return response

@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    user_or_email = (data.get("user_or_email") or "").strip()
    password = data.get("password") or ""

    if not user_or_email or not password:
        return _json_err(400, "user_or_email and password are required")

    u = User.query.filter(
        (User.email == user_or_email.lower()) | (User.username == user_or_email)
    ).first()

    if not u or not u.check_password(password):
        return _json_err(401, "Invalid credentials")

    if not u.email_verified:
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
    data = request.get_json() or {}
    email = (data.get("email") or "").lower().strip()
    if not email:
        return _json_err(400, "email required")
    u = User.query.filter_by(email=email).first()
    if not u:
        return _json_err(404, "No user with that email")
    if u.email_verified:
        return _json_err(400, "Email already verified")
    u.issue_verification(120)
    db.session.commit()
    verify_link = f"{APP_BASE}/verify/?token={u.verification_token}"
    send_email(u.email, "Verify your Brikk email", f'<p>Verify: <a href="{verify_link}">{verify_link}</a></p>')
    return jsonify({"success": True, "message": "Verification email sent"})
