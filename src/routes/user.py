# src/routes/user.py
from flask import Blueprint, jsonify, request, abort
from flask_jwt_extended import jwt_required, get_jwt, unset_jwt_cookies
from src.models.user import User, db
from src.models.customer_profile import CustomerProfile

user_bp = Blueprint("user_bp", __name__)

# ----------------------------
# User-facing endpoints
# ----------------------------

@user_bp.get("/api/me")
@jwt_required()
def me():
    """Return identity for the dashboard (name/email/plan)."""
    claims = get_jwt()
    email = claims.get("email")
    name  = claims.get("name") or ""

    plan = "free"
    prof = CustomerProfile.query.filter_by(email=email).first()
    if prof:
        plan = prof.plan or plan
        if prof.name:
            name = prof.name

    return jsonify({"email": email, "name": name, "plan": plan})


@user_bp.post("/api/profile")
@jwt_required()
def update_profile():
    """Upsert the current user's profile (name, etc)."""
    claims = get_jwt()
    email = claims.get("email")
    data = request.get_json() or {}

    prof = CustomerProfile.query.filter_by(email=email).first()
    if not prof:
        prof = CustomerProfile(email=email, name=data.get("name", ""))
        db.session.add(prof)

    if "name" in data:
        prof.name = data["name"]
    if "plan" in data:
        prof.plan = data["plan"]

    db.session.commit()
    return jsonify({"ok": True})


@user_bp.post("/api/logout")
@jwt_required(optional=True)
def logout():
    """Clear JWT cookies."""
    resp = jsonify({"ok": True})
    unset_jwt_cookies(resp)
    return resp


# ----------------------------
# Admin helpers & endpoints
# ----------------------------

def _require_admin():
    claims = get_jwt()
    roles = claims.get("roles") or []
    if "admin" not in roles:
        abort(403, description="admin only")

@user_bp.get("/api/admin/users")
@jwt_required()
def admin_get_users():
    _require_admin()
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])

@user_bp.post("/api/admin/users")
@jwt_required()
def admin_create_user():
    _require_admin()
    data = request.get_json() or {}
    user = User(username=data["username"], email=data["email"])
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

@user_bp.get("/api/admin/users/<int:user_id>")
@jwt_required()
def admin_get_user(user_id: int):
    _require_admin()
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

@user_bp.put("/api/admin/users/<int:user_id>")
@jwt_required()
def admin_update_user(user_id: int):
    _require_admin()
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    user.username = data.get("username", user.username)
    user.email    = data.get("email", user.email)
    db.session.commit()
    return jsonify(user.to_dict())

@user_bp.delete("/api/admin/users/<int:user_id>")
@jwt_required()
def admin_delete_user(user_id: int):
    _require_admin()
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return "", 204
