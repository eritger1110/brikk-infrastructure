from flask import request, g
from ..database.db import db
from ..models.audit_log import AuditLog

def log_action(action: str, resource_type: str, resource_id: str = None, metadata: dict | None = None):
    """
    Write an audit log row. The 'metadata' param is stored in the 'meta' attribute,
    whose DB column name is 'metadata' (see model).
    """
    try:
        rec = AuditLog(
            org_id=getattr(g.user, "org_id", None),
            actor_user_id=getattr(g.user, "id", None),
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            ip=(request.headers.get("X-Forwarded-For") or request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
            meta=metadata or {},  # attribute is 'meta'
        )
        db.session.add(rec)
        db.session.commit()
    except Exception:
        db.session.rollback()
