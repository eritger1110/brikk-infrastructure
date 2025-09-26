# src/routes/user.py
from __future__ import annotations

from typing import Dict, Any, Optional

from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    create_access_token,
    set_access_cookies,
    get_jwt,
)
from src.database.db import db
from src.models.user import User

user_bp = Blueprint("user", __name__, url_prefix="/api/user")


# ---- helpers ---------------------------------------------------------------

def _role_perms(role: str) -> list[str]:
    table = {
        "admin":  ["agent:create", "agent:read", "agent:update", "agent:delete"],
        "editor": ["agent:create", "agent:read", "agent:update"],
        "viewer": ["agent:read"],
    }
    return table.get(role or "viewer", ["agent:read"])


def _claims_for(user: Optional[User], email_fallback: str | None = None) -> Dict[str, Any]:
    """
    Build JWT claims from User rows (role/org) with safe defaults.
    """
    email = getattr(user, "email", None) or (email_fallback or "")
    role = getattr(user, "role", None) or "viewer"
    org_id = getattr(user, "org_id", None)

    return {
        "email": email,
        "user_id": str(getattr(user, "id", "") or ""),
        "org_id": org_id,
        "roles": [role],
        "perms": _role_perms(role),
    }


def _find_user_by_identity(ident: Any) -> Optional[User]:
    u = None
    try:
        # if identity is an int id
        u = User.query.get(int(ident))
    except Exception:
        pass
    if not u and isinstance(ident, str):
        u = User.query.filter_by(email=ident).first()
    return u


# ---- routes ----------------------------------------------------------------

@user_bp.get("/ping")
def ping():
    return jsonify({"ok": True, "service": "user"}), 200


@user_bp.get("/me")
@jwt_required(optional=True)
def me():
    ident = get_jwt_identity()
    if not ident:
        return jsonify({"authenticated": False, "user": None, "claims": None}), 200

    user = _find_user_by_identity(ident)
    if not user:
        # return minimal info from the JWT if DB row not found
        return jsonify({
            "authenticated": True,
            "user": {"id": str(ident)},
            "claims": get_jwt(),   # whatever’s in the token
        }), 200

    # include DB-backed fields and current token claims
    return jsonify({
        "authenticated": True,
        "user": user.to_dict(),
        "claims": get_jwt(),
    }), 200


@user_bp.put("/profile")
@jwt_required()
def update_profile():
    ident = get_jwt_identity()
    user = _find_user_by_identity(ident)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    if username:
        user.username = username
    db.session.commit()
    return jsonify({"user": user.to_dict()}), 200


@user_bp.post("/mint-token")
@jwt_required()
def mint_token():
    """
    Re-mint a JWT (cookie) for the current user with up-to-date roles/perms/org.
    Useful if you changed a role in the DB and want the browser to pick it up.
    """
    ident = get_jwt_identity()
    user = _find_user_by_identity(ident)
    if not user:
        return jsonify({"error": "User not found"}), 404

    claims = _claims_for(user, email_fallback=str(ident))
    token = create_access_token(identity=claims["email"] or str(ident), additional_claims=claims)

    resp = make_response(jsonify({"ok": True, "claims": claims}), 200)
    set_access_cookies(resp, token)
    return resp
