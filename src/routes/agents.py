# src/routes/agents.py
"""
Stage 1 Agents API - Create and list user agents with API key generation.

Features:
- Create agents with one-time API key generation
- List user's agents (filtered by owner_id)
- Rate limiting with admin exemption
- Audit logging for all actions
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

from flask import Blueprint, request, jsonify, g, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded

# JWT helpers (optional; we guard calls so routes work even if not present)
try:
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
except Exception:  # pragma: no cover
    verify_jwt_in_request = None
    get_jwt_identity = None
    get_jwt = None


# -----------------------------
# Per-user key + admin exempt
# -----------------------------
def current_identity() -> str | None:
    """Return JWT identity if available, else None."""
    if verify_jwt_in_request and get_jwt_identity:
        try:
            verify_jwt_in_request(optional=True)
            uid = get_jwt_identity()
            if uid:
                return str(uid)
        except Exception:
            pass
    # Fallback to g.user.id if your auth sets it without JWT
    try:
        uid = getattr(getattr(g, "user", None), "id", None)
        if uid:
            return str(uid)
    except Exception:
        pass
    return None


def is_admin() -> bool:
    """Detect admin via g.user or JWT claims."""
    # g.user check
    try:
        user = getattr(g, "user", None)
        if user:
            role = (getattr(user, "role", None) or "").lower()
            if role in {"admin", "owner"} or bool(getattr(user, "is_admin", False)):
                return True
    except Exception:
        pass

    # JWT claims check
    if get_jwt:
        try:
            verify_jwt_in_request(optional=True)
            claims = get_jwt() or {}
            role = (claims.get("role") or "").lower()
            if role in {"admin", "owner"} or bool(claims.get("is_admin")):
                return True
        except Exception:
            pass
    return False


def rate_key() -> str:
    """Use per-user key when possible; otherwise client IP."""
    uid = current_identity()
    return f"user:{uid}" if uid else get_remote_address()


limiter = Limiter(
    key_func=rate_key,
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
    strategy="moving-window",
    default_limits=["10 per second", "60 per minute"],  # global default
)

# Full prefix here; register WITHOUT extra url_prefix in main.py
agents_bp = Blueprint("agents_bp", __name__, url_prefix="/api/v1/agents")


# -----------------------------
# Helpers
# -----------------------------
def _iso(dt):
    try:
        return dt.isoformat() if dt else None
    except Exception:
        return None


def _imports_common():
    """Only what both handlers need (no schema)."""
    from src.database.db import db
    from src.models.agent import Agent
    from src.services.security import require_auth, require_perm, redact_dict
    from src.services.audit import log_action

    return db, Agent, require_auth, require_perm, redact_dict, log_action


def _imports_create():
    """Create-specific import kept separate so GET never loads schemas."""
    from src.schemas.agent import AgentCreateSchema
    from marshmallow import ValidationError

    return AgentCreateSchema, ValidationError


# JSON-as-TEXT helpers
def _encode_list(value: Any) -> str:
    """Always store list-like fields as JSON strings."""
    try:
        if isinstance(value, list):
            return json.dumps(value)
        return "[]" if value in (None, "", False) else json.dumps([value])
    except Exception:
        return "[]"


def _decode_list(value: Any):
    """Return Python list for DB value that may already be list or JSON string."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


# -----------------------------
# Error handling (JSON 429)
# -----------------------------
@agents_bp.errorhandler(RateLimitExceeded)
def _rate_limited(e: RateLimitExceeded):
    # Flask-Limiter sets Retry-After
    return jsonify({"error": "rate_limited", "message": str(e)}), 429


# -----------------------------
# GET /api/v1/agents
# -----------------------------
@agents_bp.route("", methods=["GET"])
@agents_bp.route("/", methods=["GET"])
@limiter.limit("300 per minute", exempt_when=is_admin)
def list_agents():
    """List user's agents (filtered by owner_id)"""
    db, Agent, require_auth, _, _, _ = _imports_common()

    @require_auth
    def _impl():
        # Filter by owner_id = g.user.id for Stage 1
        user_id = getattr(g.user, 'id', None)
        if not user_id:
            return jsonify({"error": "unauthorized", "message": "User ID not found"}), 401

        q = db.session.query(Agent).filter(Agent.owner_id == user_id)

        # soft-deletes
        if hasattr(Agent, "deleted_at"):
            q = q.filter(Agent.deleted_at.is_(None))

        # newest first
        if hasattr(Agent, "created_at"):
            q = q.order_by(Agent.created_at.desc())
        else:
            q = q.order_by(Agent.id.desc())

        items = []
        for a in q.limit(200).all():
            items.append(
                {
                    "id": a.id,
                    "name": a.name,
                    "description": getattr(a, "description", None),
                    "status": getattr(a, "status", "active"),
                    "created_at": _iso(getattr(a, "created_at", None)),
                }
            )
        return jsonify({"agents": items}), 200

    return _impl()


# -----------------------------
# POST /api/v1/agents
# -----------------------------
@agents_bp.route("", methods=["POST"])
@agents_bp.route("/", methods=["POST"])
@limiter.limit("10 per minute", exempt_when=is_admin)
def create_agent():
    """Create a new agent with one-time API key generation"""
    from src.database.db import db
    from src.services.crypto import generate_and_hash_api_key
    from src.services.audit import log_agent_created
    
    # Simple auth check - ensure user is authenticated
    if not hasattr(g, 'user') or not g.user:
        return jsonify({"error": "unauthorized", "message": "Authentication required"}), 401
    
    user_id = getattr(g.user, 'id', None)
    if not user_id:
        return jsonify({"error": "unauthorized", "message": "User ID not found"}), 401

    payload = request.get_json(silent=True) or {}
    
    # Basic validation
    name = payload.get('name', '').strip()
    if not name or len(name) > 128:
        return jsonify({"error": "validation_error", "message": "Name is required and must be <= 128 chars"}), 400
    
    description = payload.get('description', '').strip() or None

    # Check for duplicate name for this user
    from src.models.agent import Agent
    existing = db.session.query(Agent).filter(
        Agent.name == name,
        Agent.owner_id == user_id
    ).first()
    
    if existing:
        return jsonify({"error": "duplicate_name", "message": "Agent name already exists"}), 409

    try:
        # Generate API key and hash
        api_key, api_key_hash = generate_and_hash_api_key()
        
        # Create agent with Stage 1 fields
        agent = Agent(
            id=str(uuid.uuid4()),
            name=name,
            language="en",  # Default language
            description=description,
            owner_id=user_id,
            api_key_hash=api_key_hash,
            status="active"
        )

        db.session.add(agent)
        db.session.commit()

        # Audit log
        try:
            log_agent_created(user_id, agent.id, agent.name)
        except Exception as e:
            current_app.logger.warning(f"Failed to create audit log: {e}")

        # Return agent details with one-time API key
        return jsonify({
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "api_key": api_key,  # One-time return only
            "status": agent.status,
            "created_at": agent.created_at.isoformat() if agent.created_at else None
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create agent: {e}")
        return jsonify({"error": "internal_error", "message": "Failed to create agent"}), 500
