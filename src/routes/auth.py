# src/routes/auth.py
import os
from flask import Blueprint, current_app, jsonify, request, make_response

# Optional JWT
try:
    from flask_jwt_extended import (
        jwt_required, get_jwt_identity,
        create_access_token, set_access_cookies, unset_jwt_cookies,
    )
    HAVE_JWT = True
except Exception:
    HAVE_JWT = False

# Optional models (fine if missing)
try:
    from src.models.user import User  # type: ignore
    from src.models.purchase import Purchase  # type: ignore
    HAVE_MODELS = True
except Exception:
    HAVE_MODELS = False

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/auth/_ping", methods=["GET"])
def auth_ping():
    return jsonify({"success": True, "message": "pong",
                    "provision_secret_set": bool(os.getenv("PROVISION_SECRET"))}), 200

@auth_bp.route("/auth/_routes", methods=["GET"])
def auth_routes():
    routes = []
    for rule in current_app.url_map.iter_rules():
        if rule.rule.startswith("/api/auth"):
            methods = sorted(list(rule.methods - {"HEAD","OPTIONS"}))
            routes.append({"rule": rule.rule, "methods": methods, "endpoint": rule.endpoint})
    return jsonify({"count": len(routes), "routes": routes}), 200

@auth_bp.route("/auth/_debug-echo", methods=["GET","POST"])
def debug_echo():
    if request.method == "GET":
        return jsonify({"success": True, "method": "GET",
                        "args": request.args.to_dict(), "json_ok": False}), 200
    data = request.get_json(silent=True) or {}
    return jsonify({"success": True, "method": "POST",
                    "json_ok": isinstance(data, dict), "json": data}), 200

@auth_bp.route("/auth/complete-signup", methods=["POST"])
def complete_signup():
    # IMPORTANT: set PROVISION_SECRET='' in Render (recommended).
    required = os.getenv("PROVISION_SECRET", "").strip()
    payload = request.get_json(silent=True) or {}
    if required:
        if (payload.get("token") or "").strip() != required:
            return jsonify({"error": "bad token"}), 401

    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    first_name = payload.get("first_name") or ""
    last_name = payload.get("last_name") or ""
    if not email:    return jsonify({"error": "missing email"}), 400
    if not password: return jsonify({"error": "missing password"}), 400

    # TODO: create/persist user etc.

    resp = make_response(jsonify({
        "ok": True, "email": email,
        "first_name": first_name, "last_name": last_name
    }), 200)

    # Log the user in by setting a JWT cookie
    if HAVE_JWT:
        token = create_access_token(identity=email, additional_claims={"email": email})
        set_access_cookies(resp, token)

    return resp

# who-am-I (used by dashboard)
if HAVE_JWT:
    @auth_bp.route("/auth/me", methods=["GET","OPTIONS"])
    @jwt_required(optional=True)
    def auth_me():
        if request.method == "OPTIONS": return ("", 204)
        ident = get_jwt_identity()
        if not ident:
            return jsonify({"authenticated": False, "user": None}), 200

        if HAVE_MODELS:
            try:
                q = (User.id == ident) | (User.email == str(ident))
                user_obj = User.query.filter(q).first()
                purchase = None
                try:
                    purchase = (Purchase.query.filter_by(email=user_obj.email)
                                .order_by(Purchase.id.desc()).first()) if user_obj else None
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
                pass

        user_min = {"id": str(ident)}
        if isinstance(ident, str) and "@" in ident: user_min["email"] = ident
        return jsonify({"authenticated": True, "user": user_min}), 200
else:
    @auth_bp.route("/auth/me", methods=["GET","OPTIONS"])
    def auth_me_nojwt():
        if request.method == "OPTIONS": return ("", 204)
        return jsonify({"authenticated": False, "user": None}), 200

@auth_bp.route("/auth/logout", methods=["POST","OPTIONS"])
def logout():
    if request.method == "OPTIONS": return ("", 204)
    resp = make_response(jsonify({"ok": True}), 200)
    if HAVE_JWT: unset_jwt_cookies(resp)
    return resp

@auth_bp.route("/auth/resend-verification", methods=["POST","OPTIONS"])
def resend_verification():
    if request.method == "OPTIONS": return ("", 204)
    # TODO: integrate SendGrid later; for now pretend we sent it.
    return jsonify({"ok": True, "sent": True}), 200
