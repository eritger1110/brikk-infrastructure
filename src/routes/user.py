# src/routes/user.py
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.database.db import db
from src.models.user import User

# IMPORTANT: this symbol name must exist for main.py's import
user_bp = Blueprint("user", __name__, url_prefix="/api/user")

@user_bp.get("/ping")
def ping():
    return jsonify({"ok": True, "service": "user"})

@user_bp.get("/me")
@jwt_required()
def me():
    ident = get_jwt_identity()
    user = None
    try:
        user = User.query.get(int(ident))
    except Exception:
        user = User.query.filter_by(email=str(ident)).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": user.to_dict()})

@user_bp.put("/profile")
@jwt_required()
def update_profile():
    ident = get_jwt_identity()
    user = None
    try:
        user = User.query.get(int(ident))
    except Exception:
        user = User.query.filter_by(email=str(ident)).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    if username:
        user.username = username
    db.session.commit()
    return jsonify({"user": user.to_dict()})
