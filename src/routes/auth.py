# -*- coding: utf-8 -*-
# src/routes/auth.py
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from flask import Blueprint, current_app, jsonify, request, make_response

# --- Optional JWT (cookies) -------------------------------------------------
try:
    from flask_jwt_extended import (  # type: ignore
        jwt_required,
        get_jwt_identity,
        get_jwt,
        create_access_token,
        create_refresh_token,
        set_access_cookies,
        set_refresh_cookies,
        unset_jwt_cookies,
        verify_jwt_in_request,
    )
    HAVE_JWT = True
except Exception:
    HAVE_JWT = False

# --- Optional models (fine if missing) --------------------------------------
try:
    from src.models.user import User  # type: ignore
    from src.models.purchase import Purchase  # type: ignore
    from src.database import db  # type: ignore
    HAVE_MODELS = True
except Exception:
    HAVE_MODELS = False

# --- Optional emailer (SendGrid helper) -------------------------------------
try:
    from src.services.emailer import send_email  # type: ignore
    HAVE_EMAILER = True
except Exception:
    HAVE_EMAILER = False

# --- Token signing for email verify -----------------------------------------
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

auth_bp = Blueprint("auth", __name__)  # mounted at /api in main.py


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #
def _json() -> Dict[str, Any]:
    return (request.get_json(silent=True) or {}) if request.data else {}


def _frontend_origin() -> str:
    # where your /verify page lives
    return os.getenv("FRONTEND_ORIGIN", "https://www.getbrikk.com").rstrip("/")


def _signer() -> URLSafeTimedSerializer:
    sk = current_app.config.get("SECRET_KEY")
    if not sk:
        raise RuntimeError("SECRET_KEY is not set")
    return URLSafeTimedSerializer(sk, salt="email-verify")


def _make_token(email: str) -> str:
    return _signer().dumps({"email": email})


def _parse_token(token: str, max_age: int = 60 * 60 * 24 * 7) -> str:
    # 7-day validity
    data = _signer().loads(token, max_age=max_age)
    return str(data.get("email", "")).lower().strip()


def _send_verify_email(to_email: str) -> bool:
    """Create token, build front-end link, send email via SendGrid."""
    token = _make_token(to_email)
    verify_link = f"{_frontend_origin()}/verify?token={token}"

    current_app.logger.info(f"[verify-email] to={to_email} link={verify_link}")

    if not HAVE_EMAILER:
        current_app.logger.warning(
            "SendGrid emailer not available; skipping send")
        return False

    html = f"""
    <div style="font-family:system-ui,Segoe UI,Roboto,Arial">
      <h2>Verify your email</h2>
      <p>We're confirming <strong>{to_email}</strong> for your Brikk account.</p>
      <p>Click to verify: <a href="{verify_link}">Verify your email</a></p>
      <p style="opacity:.7">If you didn't request this, you can ignore it.</p>
      <p style="opacity:.7">Thanks,<br/>The Brikk Team</p>
    </div>
    """
    try:
        ok = bool(
            send_email(
                to_email=to_email,
                subject="Verify your email for Brikk",
                html=html,
            )
        )
        return ok
    except Exception:
        current_app.logger.exception("SendGrid send failed")
        return False


def _claims_from_user(user: "User" | None,
                      email_fallback: str | None = None) -> Dict[str, Any]:
    """Server-trusted claims to embed in JWTs."""
    if not user:
        return {
            "email": email_fallback,
            "role": "member",
            "is_admin": False,
            "org_id": None}
    role = (getattr(user, "role", None) or "member").lower()
    return {
        "role": role,
        "is_admin": role in ("owner", "admin"),
        "org_id": getattr(user, "org_id", None),
        "email": getattr(user, "email", email_fallback),
    }


# --------------------------------------------------------------------------- #
# Diagnostics
# --------------------------------------------------------------------------- #
@auth_bp.route("/auth/_ping", methods=["GET"])
def auth_ping():
    return jsonify(
        {
            "success": True,
            "message": "pong",
            "provision_secret_set": bool(os.getenv("PROVISION_SECRET")),
            "have_jwt": HAVE_JWT,
            "have_models": HAVE_MODELS,
            "have_emailer": HAVE_EMAILER,
        }
    ), 200


@auth_bp.route("/auth/_routes", methods=["GET"])
def auth_routes():
    routes = []
    for rule in current_app.url_map.iter_rules():
        if rule.rule.startswith("/api/auth"):
            methods = sorted(list(rule.methods - {"HEAD", "OPTIONS"}))
            routes.append(
                {"rule": rule.rule, "methods": methods, "endpoint": rule.endpoint}
            )
    return jsonify({"count": len(routes), "routes": routes}), 200


@auth_bp.route("/auth/_debug-echo", methods=["GET", "POST"])
def debug_echo():
    if request.method == "GET":
        return (
            jsonify(
                {
                    "success": True,
                    "method": "GET",
                    "args": request.args.to_dict(),
                    "json_ok": False,
                }
            ),
            200,
        )
    data = _json()
    return (
        jsonify(
            {
                "success": True,
                "method": "POST",
                "json_ok": isinstance(data, dict),
                "json": data,
            }
        ),
        200,
    )


# --------------------------------------------------------------------------- #
# Signup (used by /checkout/success) '" sends verification & sets initial JWT
# --------------------------------------------------------------------------- #
@auth_bp.route("/auth/complete-signup", methods=["POST", "OPTIONS"])
def complete_signup():
    if request.method == "OPTIONS":
        return ("", 204)

    payload = _json()
    # Optional shared-secret
    required_token = os.getenv("PROVISION_SECRET", "").strip()
    client_token = (payload.get("token") or "").strip()
    if required_token and client_token != required_token:
        return jsonify({"error": "bad token"}), 401

    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    first_name = (payload.get("first_name") or "").strip()
    last_name = (payload.get("last_name") or "").strip()

    if not email:
        return jsonify({"error": "missing email"}), 400
    if not password:
        return jsonify({"error": "missing password"}), 400

    user = None
    if HAVE_MODELS:
        try:
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(
                    email=email,
                    username=first_name or email.split("@")[0],
                    role="member",  # default
                )
                user.set_password(password)
                if hasattr(user, "first_name"):
                    setattr(user, "first_name", first_name)
                if hasattr(user, "last_name"):
                    setattr(user, "last_name", last_name)

                db.session.add(user)
                db.session.commit()
        except Exception:
            current_app.logger.exception("Signup upsert failed")

    sent = _send_verify_email(email)

    resp = make_response(
        jsonify(
            {
                "ok": True,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "verification_sent": bool(sent),
            }
        ),
        200,
    )

    # Set JWT cookies with server-trusted claims
    if HAVE_JWT:
        if user is None and HAVE_MODELS:
            user = User.query.filter_by(email=email).first()
        claims = _claims_from_user(user, email_fallback=email)
        ident = str(getattr(user, "id", email))
        access = create_access_token(identity=ident, additional_claims=claims)
        refresh = create_refresh_token(
            identity=ident, additional_claims=claims)
        set_access_cookies(resp, access)
        set_refresh_cookies(resp, refresh)

    return resp


# --------------------------------------------------------------------------- #
# Password login (server-trusted claims in JWT)
# --------------------------------------------------------------------------- #
@auth_bp.route("/auth/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return ("", 204)

    if not HAVE_MODELS or not HAVE_JWT:
        return jsonify({"error": "login_unavailable"}), 501

    payload = _json()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    if not email or not password:
        return jsonify({"error": "missing_credentials"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid_credentials"}), 401

    claims = _claims_from_user(user)
    access = create_access_token(
        identity=str(
            user.id),
        additional_claims=claims)
    refresh = create_refresh_token(
        identity=str(
            user.id),
        additional_claims=claims)

    resp = make_response(jsonify({"ok": True}), 200)
    set_access_cookies(resp, access)
    set_refresh_cookies(resp, refresh)
    return resp


# --------------------------------------------------------------------------- #
# Verify email token
# --------------------------------------------------------------------------- #
@auth_bp.route("/auth/verify", methods=["GET", "POST", "OPTIONS"])
def verify_email():
    if request.method == "OPTIONS":
        return ("", 204)

    token = (request.args.get("token") or "").strip()
    if not token and request.method == "POST":
        token = str((_json().get("token") or "")).strip()

    if not token:
        return jsonify({"ok": False, "error": "missing token"}), 400

    try:
        email = _parse_token(token)
    except SignatureExpired:
        return jsonify({"ok": False, "error": "token expired"}), 400
    except BadSignature:
        return jsonify({"ok": False, "error": "bad token"}), 400

    # Optional: mark verified in DB
    if HAVE_MODELS:
        try:
            user = User.query.filter_by(email=email).first()
            if user and hasattr(user, "email_verified"):
                setattr(user, "email_verified", True)
                db.session.commit()
        except Exception:
            current_app.logger.exception(
                "verify: could not persist email_verified")

    return jsonify({"ok": True, "email": email}), 200


# --------------------------------------------------------------------------- #
# Who am I?  (dashboard)
# --------------------------------------------------------------------------- #
if HAVE_JWT:

    @auth_bp.route("/auth/me", methods=["GET", "OPTIONS"])
    @jwt_required(optional=True)
    def auth_me():
        if request.method == "OPTIONS":
            return ("", 204)

        ident = get_jwt_identity()
        claims = get_jwt() if ident else {}
        if not ident:
            return jsonify({"authenticated": False, "user": None}), 200

        if HAVE_MODELS:
            try:
                # allow lookup by id or email if identity was email
                q = (User.id == ident) | (User.email == str(ident))
                user_obj = User.query.filter(q).first()
                purchase = None
                try:
                    if user_obj and 'Purchase' in globals() and hasattr(Purchase, "email"):
                        purchase = (
                            Purchase.query.filter_by(email=user_obj.email)
                            .order_by(Purchase.id.desc())
                            .first()
                        )
                except Exception:
                    purchase = None

                if user_obj:
                    return (
                        jsonify(
                            {
                                "authenticated": True,
                                "user": {
                                    "id": str(getattr(user_obj, "id", "") or ""),
                                    "email": getattr(user_obj, "email", None),
                                    "username": getattr(user_obj, "username", None),
                                    "email_verified": bool(getattr(user_obj, "email_verified", False)),
                                    "role": (getattr(user_obj, "role", None) or "member").lower(),
                                    "org_id": getattr(user_obj, "org_id", None),
                                    "is_admin": user_obj.is_admin,
                                },
                                "order_ref": getattr(purchase, "order_ref", None),
                                "claims": {k: claims.get(k) for k in ("role", "is_admin", "org_id", "email")},
                            }
                        ),
                        200,
                    )
            except Exception:
                current_app.logger.exception("auth/me enrichment failed")

        # fallback when no model
        user_min: Dict[str, Any] = {"id": str(ident)}
        if isinstance(ident, str) and "@" in ident:
            user_min["email"] = ident
        user_min.update({k: claims.get(k)
                        for k in ("role", "is_admin", "org_id") if k in claims})
        return jsonify({"authenticated": True, "user": user_min}), 200

else:

    @auth_bp.route("/auth/me", methods=["GET", "OPTIONS"])
    def auth_me_nojwt():
        if request.method == "OPTIONS":
            return ("", 204)
        return jsonify({"authenticated": False, "user": None}), 200


# --------------------------------------------------------------------------- #
# Logout (clears the cookie)
# --------------------------------------------------------------------------- #
@auth_bp.route("/auth/logout", methods=["POST", "OPTIONS"])
def logout():
    if request.method == "OPTIONS":
        return ("", 204)
    resp = make_response(jsonify({"ok": True}), 200)
    if HAVE_JWT:
        unset_jwt_cookies(resp)
    return resp


# --------------------------------------------------------------------------- #
# Resend verification (POST)
# --------------------------------------------------------------------------- #
@auth_bp.route("/auth/resend-verification", methods=["POST", "OPTIONS"])
def resend_verification():
    if request.method == "OPTIONS":
        return ("", 204)

    to_email: Optional[str] = None
    if HAVE_JWT:
        try:
            verify_jwt_in_request(optional=True)
            ident = get_jwt_identity()
            if isinstance(ident, str) and "@" in ident:
                to_email = ident
        except Exception:
            pass

    payload = _json()
    if not to_email:
        e = (payload.get("email") or "").strip().lower()
        if e:
            to_email = e

    if not to_email:
        return jsonify({"ok": False, "error": "email required"}), 400

    ok = _send_verify_email(to_email)
    return jsonify({"ok": ok, "sent": ok}), (200 if ok else 502)


# --------------------------------------------------------------------------- #
# Email test helper
# --------------------------------------------------------------------------- #
@auth_bp.route("/auth/_email-test", methods=["POST", "OPTIONS"])
def email_test():
    if request.method == "OPTIONS":
        return ("", 204)

    if not HAVE_EMAILER:
        return jsonify({"ok": False, "reason": "emailer-unavailable"}), 501

    to_email = None
    try:
        if HAVE_JWT:
            verify_jwt_in_request(optional=True)
            ident = get_jwt_identity()
            if isinstance(ident, str) and "@" in ident:
                to_email = ident
    except Exception:
        pass

    payload = _json()
    to_email = to_email or (payload.get("email") or "").strip().lower()
    if not to_email:
        return jsonify({"ok": False, "error": "email required"}), 400

    html = f"<p>Brikk test email to <strong>{to_email}</strong>. If you see this, SendGrid works '...</p>"
    try:
        ok = bool(
            send_email(
                to_email=to_email,
                subject="Brikk test email",
                html=html))
        return jsonify({"ok": ok}), (200 if ok else 502)
    except Exception as e:
        current_app.logger.exception("email-test failed")
        return jsonify({"ok": False, "error": repr(e)}), 500
