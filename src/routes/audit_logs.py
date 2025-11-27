# -*- coding: utf-8 -*-
"""
Audit logs routes for viewing organization activity.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from src.models.audit_log import AuditLog

audit_logs_bp = Blueprint("audit_logs", __name__, url_prefix="/api/audit-logs")


@audit_logs_bp.get("")
@jwt_required()
def get_audit_logs():
    """
    Get audit logs for the organization.
    GET /api/audit-logs?page=1&limit=50
    """
    claims = get_jwt()
    org_id = claims.get("org_id")
    
    if not org_id:
        return jsonify({"error": "No organization associated with user"}), 400
    
    # Check admin permission
    roles = claims.get("roles", [])
    if not any(r in ["admin", "owner"] for r in roles):
        return jsonify({"error": "Admin access required"}), 403
    
    # Pagination
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 50, type=int), 100)  # Max 100
    
    # Query audit logs
    query = AuditLog.query.filter_by(org_id=org_id).order_by(AuditLog.timestamp.desc())
    
    # Apply pagination
    paginated = query.paginate(page=page, per_page=limit, error_out=False)
    
    logs = [{
        "id": log.id,
        "org_id": log.org_id,
        "user_email": log.user_email,
        "action": log.action,
        "details": log.details,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None
    } for log in paginated.items]
    
    return jsonify({
        "logs": logs,
        "total": paginated.total,
        "page": page,
        "pages": paginated.pages,
        "has_next": paginated.has_next,
        "has_prev": paginated.has_prev
    }), 200
