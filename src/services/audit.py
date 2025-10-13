# src/services/audit.py
from typing import Any, Dict, Optional
from flask import request, g, current_app

from src.database import db
from src.models.audit_log import AuditLog


def log_action(
    actor_id: Optional[str] = None,
    action: str = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Log an audit action to the database.
    
    Args:
        actor_id: UUID of the user performing the action (defaults to g.user.id)
        action: Action being performed (e.g., "agent.created", "echo.sent")
        resource_type: Type of resource being acted upon (e.g., "agent", "message")
        resource_id: UUID of the specific resource
        metadata: Additional context data
    
    Returns:
        The created AuditLog instance
    """
    try:
        # Use provided actor_id or fall back to current user
        if actor_id is None:
            actor_id = getattr(g, 'user', None)
            if actor_id:
                actor_id = getattr(actor_id, 'id', None)
        
        if not actor_id:
            current_app.logger.warning("No actor_id available for audit log")
            return None
            
        audit_log = AuditLog(
            actor_id=str(actor_id),
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            metadata=metadata or {}
        )
        
        db.session.add(audit_log)
        db.session.commit()
        
        current_app.logger.info(
            f"Audit log created: actor={actor_id} action={action} "
            f"resource={resource_type}:{resource_id}"
        )
        
        return audit_log
        
    except Exception as e:
        current_app.logger.error(f"Failed to create audit log: {e}")
        db.session.rollback()
        raise


def log_agent_created(actor_id: str, agent_id: str, agent_name: str) -> AuditLog:
    """Convenience method for logging agent creation"""
    return log_action(
        actor_id=actor_id,
        action="agent.created",
        resource_type="agent",
        resource_id=agent_id,
        metadata={"agent_name": agent_name}
    )


def log_echo_sent(actor_id: str, message_id: str, sender_id: str) -> AuditLog:
    """Convenience method for logging echo messages"""
    return log_action(
        actor_id=actor_id,
        action="echo.sent",
        resource_type="message",
        resource_id=message_id,
        metadata={"sender_id": sender_id}
    )


# Backward compatibility function for existing code
def log_action_legacy(action: str, resource_type: str, resource_id: str = None, metadata: dict = None):
    """
    Legacy function for backward compatibility.
    Write an audit log row using the old signature.
    """
    return log_action(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata
    )
