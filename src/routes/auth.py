# src/routes/auth.py
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from flask import Blueprint, current_app, jsonify, request, make_response

# ---------------- Optional JWT (cookies) ------------------------------------
try:
    from flask_jwt_extended import (  # type: ignore
        jwt_required,
        get_jwt_identity,
        create_access_token,
        set_access_cookies,
        unset_jwt_cookies,
        verify_jwt_in_request,
    )
    HAVE_JWT = True
except Exception:  # pragma: no cover
    HAVE_JWT = False

# ---------------- Optional models (fine if missing) -------------------------
try:
    from src.models.user import User  # type: ignore
    from src.models.purchase import Purchase  # type: ignore
    HAVE_MODELS = True
except Exception:  # pragma: no cover
    HAVE_MODELS = False

# ---------------- Optional emailer (SendGrid helper) ------------------------
try:
    from src.services.emailer import send_email  # type: ignore
    HAVE_EMAILER = True
except Exception:  # pragma: no cover
    HAVE_EMAILER = False

# ---------------- Token signer for email verification -----------------------
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

auth_bp = Blueprint("auth", __name__)  # mounted at /api in main.py


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #
def _json() -> Dict[str, Any]:
    return (request.get_json(silent=True) or {}) if request.data else {}


def _signer() -> URLSafeTimedSerializer:
    # Uses Flask SECRET_KEY; add extra salt for separation of concerns
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="email-verify")


def _make_verify_token(email: str) -> str:
    return _signer().dumps({"email": (email or "").strip().lower()})


def _parse_verify_token(token: str, max_age: int = 60 * 60 * 24 * 7) -> str:
    # Default validity: 7 days
    data = _signer().loads(token, max_age=max_age)
    return str(data.get("email", "")).lower().strip()


def _frontend_origin() -> str:
    # Where /verify lives
    return os.getenv("FRONTEND_ORIGIN", "https://www.getbrikk.com").rstrip("/")


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
    return jsonify({"success": True, "method": "POST", "json_ok": True, "json": data}), 200


# --------------------------------------------------------------------------- #
# Signup (used by /checkout/success) – now also sends verification email
# --------------------------------------------------------------------------- #
@auth_bp.route("/auth/complete-signup", methods=["POST", "OPTIONS"])
def complete_signup():
    if request.method == "OPTIONS":
        return ("", 204)

    payload = _json()

    # If you set PROVISION_SECRET, require the client token. Otherwise, skip.
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

    # Optional: upsert a minimal user if models are available
    if HAVE_MODELS:
        try:
            existing = User.query.filter_by(email=email).first()
            if not existing:
                u = User(email=email, username=first_name or email.split("@")[0])
                if hasattr(u, "set_password"):
                    u.set_password(password)
                if hasattr(u, "first_name"):
                    setattr(u, "first_name", first_name)
                if hasattr(u, "last_name"):
                    setattr(u, "last_name", last_name)
                from src.database.db import db  # lazy import

                db.session.add(u)
                db.session.commit()
        except Exception:
            current_app.logger.exception("Signup upsert failed")

    # Prepare response and set JWT cookie if available
    resp = make_response(
        jsonify(
            {
                "ok": True,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "verification_email_queued": bool(HAVE_EMAILER),
            }
        ),
        200,
    )
    if HAVE_JWT:
        token = create_access_token(identity=email, additional_claims={"email": email})
        set_access_cookies(resp, token)

    # Fire-and-forget verification email (don’t block response)
    if HAVE_EMAILER:
        try:
            vtoken = _make_verify_token(email)
            verify_link = f"{_frontend_origin()}/verify?token={vtoken}"
            html = f"""
            <div style="font-family:system-ui,Segoe UI,Roboto,Arial">
              <h2>Verify your email</h2>
              <p>Welcome{', ' + first_name if first_name else ''}! Click below to verify:</p>
              <p><a href="{verify_link}">Verify your Brikk email</a></p>
              <p style="opacity:.7">If you didn’t request this, you can ignore it.</p>
            </div>
            """
            send_email(to_email=email, subject="Verify your Brikk email", html=html)
        except Exception:
            current_app.logger.exception("signup: sending verification email failed")

    return resp


# --------------------------------------------------------------------------- #
# Verify – GET /api/auth/verify?token=...
# --------------------------------------------------------------------------- #
@auth_bp.route("/auth/verify", methods=["GET"])
def verify_email():
    token = (request.args.get("token") or "").strip()
    if not token:
        return jsonify({"ok": False, "error": "missing token"}), 400

    try:
        email = _parse_verify_token(token)
    except SignatureExpired:
        return jsonify({"ok": False, "error": "token expired"}), 400
    except BadSignature:
        return jsonify({"ok": False, "error": "bad token"}), 400
    except Exception:
        current_app.logger.exception("verify: unexpected error")
        return jsonify({"ok": False, "error": "server error"}), 500

    # If you have a user model, mark as verified
    if HAVE_MODELS:
        try:
            u = User.query.filter_by(email=email).first()
            if u and hasattr(u, "email_verified"):
                setattr(u, "email_verified", True)
                from src.database.db import db
                db.session.commit()
        except Exception:
            current_app.logger.exception("verify: could not set email_verified")

    return jsonify({"ok": True, "email": email}), 200


# --------------------------------------------------------------------------- #
# Resend verification email (uses SendGrid helper)
# --------------------------------------------------------------------------- #
@auth_bp.route("/auth/resend-verification", methods=["POST", "OPTIONS"])
def resend_verification():
    if request.method == "OPTIONS":
        return ("", 204)

    # Prefer logged-in email from JWT; else accept {email}
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
    if not HAVE_EMAILER:
        current_app.logger.warning("SendGrid emailer not available; skipping send")
        return jsonify({"ok": False, "sent": False, "reason": "emailer-unavailable"}), 501

    try:
        vtoken = _make_verify_token(to_email)
        verify_link = f"{_frontend_origin()}/verify?token={vtoken}"
        html = f"""
        <div style="font-family:system-ui,Segoe UI,Roboto,Arial">
          <h2>Verify your email</h2>
          <p>We’re confirming <strong>{to_email}</strong> for your Brikk account.</p>
          <p>Click to verify: <a href="{verify_link}">Verify</a></p>
          <p style="opacity:.7">If you didn’t request this, you can ignore it.</p>
        </div>
        """
        ok = bool(
            send_email(to_email=to_email, subject="Verify your Brikk email", html=html)
        )
    except Exception:
        current_app.logger.exception("resend: SendGrid send failed")
        ok = False

    return jsonify({"ok": ok, "sent": ok}), (200 if ok else 502)


# --------------------------------------------------------------------------- #
# Simple test email endpoint (optional)
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

    html = f"<p>Brikk test email to <strong>{to_email}</strong>. If you see this, SendGrid works ✅</p>"
    text = f"Brikk test email to {to_email}. If you see this, SendGrid works."
    try:
        ok = send_email(to_email=to_email, subject="Brikk test email", html=html, text=text)
        return jsonify({"ok": bool(ok)}), (200 if ok else 502)
    except Exception as e:
        current_app.logger.exception("email-test failed")
        return jsonify({"ok": False, "error": repr(e)}), 500


# --------------------------------------------------------------------------- #
# Who am I? (used by dashboard)
# --------------------------------------------------------------------------- #
if HAVE_JWT:

    @auth_bp.route("/auth/me", methods=["GET", "OPTIONS"])
    @jwt_required(optional=True)
    def auth_me():
        if request.method == "OPTIONS":
            return ("", 204)

        ident = get_jwt_identity()
        if not ident:
            return jsonify({"authenticated": False, "user": None}), 200

        # Enrich from DB if available
        if HAVE_MODELS:
            try:
                q = (User.id == ident) | (User.email == str(ident))
                user_obj = User.query.filter(q).first()
                purchase = None
                try:
                    if user_obj and hasattr(Purchase, "email"):
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
                                    "email_verified": bool(
                                        getattr(user_obj, "email_verified", False)
                                    ),
                                },
                                "order_ref": getattr(purchase, "order_ref", None),
                            }
                        ),
                        200,
                    )
            except Exception:
                current_app.logger.exception("auth/me enrichment failed")

        # Fallback minimal payload from JWT
        user_min: Dict[str, Any] = {"id": str(ident)}
        if isinstance(ident, str) and "@" in ident:
            user_min["email"] = ident
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
