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
        create_access_token,
        set_access_cookies,
        unset_jwt_cookies,
    )
    HAVE_JWT = True
except Exception:  # pragma: no cover
    HAVE_JWT = False

# --- Optional models (fine if missing) --------------------------------------
try:
    from src.models.user import User  # type: ignore
    from src.models.purchase import Purchase  # type: ignore
    HAVE_MODELS = True
except Exception:  # pragma: no cover
    HAVE_MODELS = False

auth_bp = Blueprint("auth", __name__)  # mounted at /api in main.py


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #

def _bool_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip() in {"1", "true", "TRUE", "yes", "on"}

def _json() -> Dict[str, Any]:
    return (request.get_json(silent=True) or {}) if request.data else {}


# --------------------------------------------------------------------------- #
# Diagnostics
# --------------------------------------------------------------------------- #

@auth_bp.route("/auth/_ping", methods=["GET"])
def auth_ping():
    return jsonify({
        "success": True,
        "message": "pong",
        "provision_secret_set": bool(os.getenv("PROVISION_SECRET")),
    }), 200


@auth_bp.route("/auth/_routes", methods=["GET"])
def auth_routes():
    routes = []
    for rule in current_app.url_map.iter_rules():
        if rule.rule.startswith("/api/auth"):
            methods = sorted(list(rule.methods - {"HEAD", "OPTIONS"}))
            routes.append({
                "rule": rule.rule,
                "methods": methods,
                "endpoint": rule.endpoint,
            })
    return jsonify({"count": len(routes), "routes": routes}), 200


@auth_bp.route("/auth/_debug-echo", methods=["GET", "POST"])
def debug_echo():
    if request.method == "GET":
        return jsonify({
            "success": True,
            "method": "GET",
            "args": request.args.to_dict(),
            "json_ok": False,
        }), 200
    data = _json()
    return jsonify({
        "success": True,
        "method": "POST",
        "json_ok": isinstance(data, dict),
        "json": data,
    }), 200


# --------------------------------------------------------------------------- #
# Signup (used by /checkout/success)
# --------------------------------------------------------------------------- #

@auth_bp.route("/auth/complete-signup", methods=["POST", "OPTIONS"])
def complete_signup():
    if request.method == "OPTIONS":
        # CORS preflight handled by Flask-CORS; keep the 204 fast path
        return ("", 204)

    payload = _json()
    # IMPORTANT:
    # In production we recommend leaving PROVISION_SECRET empty (unset) so
    # the Netlify indirection is not required. If you do set it, the client
    # must include { token: <secret> }.
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

    # NOTE: This stub intentionally does not persist to a DB so you can run
    # without models. If you have models, try to upsert a minimal user.
    if HAVE_MODELS:
        try:
            existing = User.query.filter_by(email=email).first()
            if not existing:
                # Create a minimal user; adapt fields to your model.
                u = User(email=email, username=first_name or email.split("@")[0])
                # If you have a setter/hasher, call it here:
                if hasattr(u, "set_password"):
                    u.set_password(password)
                # Best-effort for names:
                if hasattr(u, "first_name"):
                    setattr(u, "first_name", first_name)
                if hasattr(u, "last_name"):
                    setattr(u, "last_name", last_name)
                from src.database.db import db  # lazy import
                db.session.add(u)
                db.session.commit()
        except Exception:
            # Non-fatal: we still log the user in via cookie below
            current_app.logger.exception("Signup upsert failed")

    # Create response and (optionally) attach JWT cookie
    resp = make_response(jsonify({
        "ok": True,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
    }), 200)

    if HAVE_JWT:
        claims = {"email": email}
        # identity can be email (string). If you have numeric IDs, use that.
        token = create_access_token(identity=email, additional_claims=claims)
        # Uses JWT_* cookie settings from main.py
        set_access_cookies(resp, token)

    return resp


# --------------------------------------------------------------------------- #
# Who am I?  (dashboard uses this)
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

        # If models are available, enrich the response.
        if HAVE_MODELS:
            try:
                q = (User.id == ident) | (User.email == str(ident))
                user_obj = User.query.filter(q).first()
                purchase = None
                try:
                    if user_obj and hasattr(Purchase, "email"):
                        purchase = (Purchase.query.filter_by(email=user_obj.email)
                                    .order_by(Purchase.id.desc()).first())
                except Exception:
                    purchase = None

                if user_obj:
                    return jsonify({
                        "authenticated": True,
                        "user": {
                            "id": str(getattr(user_obj, "id", "") or ""),
                            "email": getattr(user_obj, "email", None),
                            "username": getattr(user_obj, "username", None),
                            "email_verified": bool(getattr(user_obj, "email_verified", False)),
                        },
                        "order_ref": getattr(purchase, "order_ref", None),
                    }), 200
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


# --------------------------------------------------------------------------- #
# Resend verification (stub – wire SendGrid later)
# --------------------------------------------------------------------------- #

@auth_bp.route("/auth/resend-verification", methods=["POST", "OPTIONS"])
def resend_verification():
    if request.method == "OPTIONS":
        return ("", 204)
    # TODO: integrate SendGrid; for now we just pretend it was sent.
    return jsonify({"ok": True, "sent": True}), 200
