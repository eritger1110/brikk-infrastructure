# -*- coding: utf-8 -*-
"""
Organization management routes for user/team management.
Handles user invites, role management, and org settings.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy.exc import IntegrityError
from src.database import db
from src.models.user import User
from src.models.org import Organization
from src.models.audit_log import AuditLog
import secrets
from datetime import datetime, timezone

org_mgmt_bp = Blueprint("org_management", __name__, url_prefix="/api/org")


def _require_admin(claims: dict):
    """Check if user has admin or owner role."""
    roles = claims.get("roles", [])
    if not any(r in ["admin", "owner"] for r in roles):
        return jsonify({"error": "Admin access required"}), 403
    return None


def _log_audit(org_id: str, user_email: str, action: str, details: dict):
    """Create audit log entry."""
    try:
        log = AuditLog(
            org_id=org_id,
            user_email=user_email,
            action=action,
            details=str(details),
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Failed to create audit log: {e}")


@org_mgmt_bp.get("/users")
@jwt_required()
def list_users():
    """
    List all users in the organization.
    GET /api/org/users
    """
    claims = get_jwt()
    org_id = claims.get("org_id")
    
    if not org_id:
        return jsonify({"error": "No organization associated with user"}), 400
    
    # Get all users in the org
    users = User.query.filter_by(org_id=org_id).all()
    
    return jsonify({
        "users": [u.to_dict() for u in users],
        "total": len(users)
    }), 200


@org_mgmt_bp.post("/users/invite")
@jwt_required()
def invite_user():
    """
    Invite a new user to the organization.
    POST /api/org/users/invite
    Body: {"email": "user@example.com", "role": "member"}
    """
    claims = get_jwt()
    org_id = claims.get("org_id")
    user_email = claims.get("email")
    
    # Check admin permission
    admin_check = _require_admin(claims)
    if admin_check:
        return admin_check
    
    if not org_id:
        return jsonify({"error": "No organization associated with user"}), 400
    
    data = request.get_json() or {}
    invite_email = (data.get("email") or "").strip().lower()
    role = (data.get("role") or "member").lower()
    
    if not invite_email:
        return jsonify({"error": "Email is required"}), 400
    
    # Validate role
    if role not in ["owner", "admin", "member", "viewer"]:
        return jsonify({"error": "Invalid role. Must be: owner, admin, member, or viewer"}), 400
    
    # Check if user already exists
    existing = User.query.filter_by(email=invite_email, org_id=org_id).first()
    if existing:
        return jsonify({"error": "User already exists in organization"}), 409
    
    # Create user with invite token
    try:
        new_user = User(
            email=invite_email,
            username=invite_email.split("@")[0],  # Default username
            password_hash="",  # Will be set when they accept invite
            role=role,
            org_id=org_id,
            email_verified=False
        )
        new_user.issue_verification(minutes=10080)  # 7 days
        
        db.session.add(new_user)
        db.session.commit()
        
        # Log audit event
        _log_audit(org_id, user_email, "user_invited", {
            "invited_email": invite_email,
            "role": role
        })
        
        # TODO: Send invite email with verification_token
        # For now, return the token in response (remove in production)
        
        return jsonify({
            "message": "User invited successfully",
            "user": new_user.to_dict(),
            "invite_token": new_user.verification_token  # Remove in production
        }), 201
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "User with this email already exists"}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to invite user: {str(e)}"}), 500


@org_mgmt_bp.put("/users/<int:user_id>/role")
@jwt_required()
def update_user_role(user_id: int):
    """
    Update a user's role in the organization.
    PUT /api/org/users/:id/role
    Body: {"role": "admin"}
    """
    claims = get_jwt()
    org_id = claims.get("org_id")
    user_email = claims.get("email")
    
    # Check admin permission
    admin_check = _require_admin(claims)
    if admin_check:
        return admin_check
    
    if not org_id:
        return jsonify({"error": "No organization associated with user"}), 400
    
    data = request.get_json() or {}
    new_role = (data.get("role") or "").lower()
    
    if not new_role:
        return jsonify({"error": "Role is required"}), 400
    
    # Validate role
    if new_role not in ["owner", "admin", "member", "viewer"]:
        return jsonify({"error": "Invalid role. Must be: owner, admin, member, or viewer"}), 400
    
    # Get user
    user = User.query.filter_by(id=user_id, org_id=org_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Prevent changing own role
    if user.email == user_email:
        return jsonify({"error": "Cannot change your own role"}), 403
    
    old_role = user.role
    user.role = new_role
    db.session.commit()
    
    # Log audit event
    _log_audit(org_id, user_email, "user_role_changed", {
        "user_id": user_id,
        "user_email": user.email,
        "old_role": old_role,
        "new_role": new_role
    })
    
    return jsonify({
        "message": "User role updated successfully",
        "user": user.to_dict()
    }), 200


@org_mgmt_bp.delete("/users/<int:user_id>")
@jwt_required()
def remove_user(user_id: int):
    """
    Remove a user from the organization.
    DELETE /api/org/users/:id
    """
    claims = get_jwt()
    org_id = claims.get("org_id")
    user_email = claims.get("email")
    
    # Check admin permission
    admin_check = _require_admin(claims)
    if admin_check:
        return admin_check
    
    if not org_id:
        return jsonify({"error": "No organization associated with user"}), 400
    
    # Get user
    user = User.query.filter_by(id=user_id, org_id=org_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Prevent removing self
    if user.email == user_email:
        return jsonify({"error": "Cannot remove yourself"}), 403
    
    # Prevent removing last owner
    if user.role == "owner":
        owner_count = User.query.filter_by(org_id=org_id, role="owner").count()
        if owner_count <= 1:
            return jsonify({"error": "Cannot remove the last owner"}), 403
    
    removed_email = user.email
    db.session.delete(user)
    db.session.commit()
    
    # Log audit event
    _log_audit(org_id, user_email, "user_removed", {
        "user_id": user_id,
        "removed_email": removed_email
    })
    
    return jsonify({"message": "User removed successfully"}), 200


@org_mgmt_bp.put("/settings")
@jwt_required()
def update_org_settings():
    """
    Update organization settings.
    PUT /api/org/settings
    Body: {"name": "New Name", "contact_email": "contact@example.com"}
    """
    claims = get_jwt()
    org_id = claims.get("org_id")
    user_email = claims.get("email")
    
    # Check admin permission
    admin_check = _require_admin(claims)
    if admin_check:
        return admin_check
    
    if not org_id:
        return jsonify({"error": "No organization associated with user"}), 400
    
    # Get organization
    org = Organization.query.filter_by(id=org_id).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404
    
    data = request.get_json() or {}
    
    # Update allowed fields
    if "name" in data:
        org.name = data["name"].strip()
    if "description" in data:
        org.description = data["description"]
    if "contact_email" in data:
        org.contact_email = data["contact_email"].strip()
    if "contact_name" in data:
        org.contact_name = data["contact_name"].strip()
    
    db.session.commit()
    
    # Log audit event
    _log_audit(org_id, user_email, "org_settings_updated", {
        "updated_fields": list(data.keys())
    })
    
    return jsonify({
        "message": "Organization settings updated successfully",
        "organization": org.to_dict()
    }), 200


@org_mgmt_bp.get("/me")
@jwt_required()
def get_current_org():
    """
    Get current user's organization details.
    GET /api/org/me
    """
    claims = get_jwt()
    org_id = claims.get("org_id")
    
    if not org_id:
        return jsonify({"error": "No organization associated with user"}), 400
    
    org = Organization.query.filter_by(id=org_id).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404
    
    return jsonify(org.to_dict()), 200
