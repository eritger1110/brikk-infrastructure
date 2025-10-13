# -*- coding: utf-8 -*-
# src/routes/dev_login.py
from __future__ import annotations
import os
from datetime import timedelta
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, set_access_cookies

dev_bp = Blueprint("dev_login", __name__)  # mounted under /api


def _dev_enabled() -> bool:
    return os.getenv("ENABLE_DEV_LOGIN", "0") == "1"


@dev_bp.route("/auth/dev-login", methods=["POST", "OPTIONS"])
def dev_login():
    # Let CORS preflight succeed without touching the body.
    if request.method == "OPTIONS":
        return ("", 204)

    if not _dev_enabled():
        return jsonify({"error": "dev login disabled"}), 404

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "email required"}), 400

    # 7-day token for testing only
    access = create_access_token(
        identity=email,
        expires_delta=timedelta(
            days=7))

    resp = jsonify({"ok": True, "identity": email})
    set_access_cookies(
        resp, access, max_age=int(
            timedelta(
                days=7).total_seconds()))
    return resp, 200
