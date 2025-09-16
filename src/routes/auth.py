# at the top of the file
from flask import Blueprint, request, jsonify
import os

PROVISION_SECRET = os.getenv("PROVISION_SECRET", "").strip()
auth_bp = Blueprint("auth", __name__)

@auth_bp.post("/auth/complete-signup")
def complete_signup():
    data = request.get_json(silent=True) or {}
    # accept token from body or Authorization header
    body_token = (data.get("token") or "").strip()
    hdr = (request.headers.get("Authorization") or "").strip()
    hdr_token = ""
    if hdr.lower().startswith("bearer "):
        hdr_token = hdr.split(" ", 1)[1].strip()
    elif hdr.lower().startswith("provision "):
        hdr_token = hdr.split(" ", 1)[1].strip()

    token = body_token or hdr_token

    if PROVISION_SECRET:
        if not token or token != PROVISION_SECRET:
            return jsonify({"error": "bad token"}), 401
# src/routes/auth.py
import os
from flask import Blueprint, current_app, jsonify, request

auth_bp = Blueprint("auth", __name__)  # exported below as variable named auth_bp

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

# ---- the endpoint your success page calls
@auth_bp.route("/auth/complete-signup", methods=["POST"])
def complete_signup():
    # Optional provisioning guard (NO JWT decode here)
    required = os.getenv("PROVISION_SECRET")
    payload = request.get_json(silent=True) or {}

    if required:
        token = (payload.get("token") or "").strip()
        if token != required:
            return jsonify({"error": "bad token"}), 401

    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    first_name = payload.get("first_name") or ""
    last_name = payload.get("last_name") or ""

    if not email:
        return jsonify({"error": "missing email"}), 400
    if not password:
        return jsonify({"error": "missing password"}), 400

    # TODO: create the user, set cookies, etc.
    # For now, just prove the flow works:
    return jsonify({
        "ok": True,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
    }), 200
