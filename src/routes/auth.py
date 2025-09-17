# src/routes/auth.py

import os
from flask import Blueprint, current_app, jsonify, request

# Optional (used by /auth/me if JWT cookies are set)
try:
    from flask_jwt_extended import jwt_required, get_jwt_identity  # type: ignore
    HAVE_JWT = True
except Exception:
    HAVE_JWT = False

# Optional (used by /auth/me to enrich the response if models exist)
try:
    from src.models.user import User  # type: ignore
    from src.models.purchase import Purchase  # type: ignore
    HAVE_MODELS = True
except Exception:
    HAVE_MODELS = False

auth_bp = Blueprint("auth", __name__)  # mounted under /api in main.py


# ---- simple health-ish ping for the auth area
@auth_bp.route("/auth/_ping", methods=["GET"])
def auth_ping():
    return jsonify({
        "success": True,
        "message": "pong",
        "provision_secret_set": bool(os.getenv("PROVISION_SECRET")),
    }), 200


# ---- list the routes we registered (handy for proving what Flask sees)
@auth_bp.route("/auth/_routes", methods=["GET"])
def auth_routes():
    routes = []
    for rule in current_app.url_map.iter_rules():
        if rule.rule.startswith("/api/auth"):
            methods = sorted(list(rule.methods - {"HEAD", "OPTIONS"}))
            routes.append({"rule": rule.rule, "methods": methods, "endpoint": rule.endpoint})
    return jsonify({"count": len(routes), "routes": routes}), 200


# ---- echo to prove CORS + body parsing works
@auth_bp.route("/auth/_debug-echo", methods=["GET", "POST"])
def debug_echo():
    if request.method == "GET":
        return jsonify({
            "success": True,
            "method": "GET",
            "args": request.args.to_dict(),
            "json_ok": False,
        }), 200

    data = request.get_json(silent=True) or {}
    return jsonify({
        "success": True,
        "method": "POST",
        "json_ok": isinstance(data, dict),
        "json": data,
    }), 200


# ---- complete-signup (kept as-is, guarded by PROVISION_SECRET if set)
@auth_bp.route("/auth/complete-signup", methods=["POST"])
def complete_signup():
    required = os.getenv("PROVISION_SECRET", "").strip(_
