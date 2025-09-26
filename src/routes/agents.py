# src/routes/agents.py
"""
Agents endpoints (lazy imports so blueprint always registers cleanly).

We store list-like fields (capabilities, tags) as JSON-encoded TEXT on write,
and decode them on read. This works with SQLite immediately and is also safe
for Postgres/MySQL (the ORM will accept TEXT for JSON as well).
"""

import json
from typing import Any

from flask import Blueprint, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Exported limiter; main.py calls limiter.init_app(app)
limiter = Limiter(key_func=get_remote_address)

# Full prefix here; in main.py register WITHOUT extra url_prefix
agents_bp = Blueprint("agents_bp", __name__, url_prefix="/api/v1/agents")


def _iso(dt):
    try:
        return dt.isoformat() + "Z" if dt else None
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


# ---------- helpers for JSON-as-TEXT storage ----------
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


# ---------- GET /api/v1/agents ----------
@agents_bp.route("", methods=["GET"])
@agents_bp.route("/", methods=["GET"])
def list_agents():
    db, Agent, require_auth, _, _, _ = _imports_common()

    @require_auth
    def _impl():
        q = db.session.query(Agent)

        # soft-deletes
        if hasattr(Agent, "deleted_at"):
            q = q.filter(Agent.deleted_at.is_(None))

        # newest first
        if hasattr(Agent, "created_at"):
            q = q.order_by(Agent.created_at.desc())
        else:
            q = q.order_by(Agent.id.desc())

        # optional org scoping
        if hasattr(Agent, "org_id") and hasattr(g, "user") and getattr(g.user, "org_id", None):
            q = q.filter(Agent.org_id == g.user.org_id)

        items = []
        for a in q.limit(200).all():
            items.append({
                "id": a.id,
                "name": a.name,
                "description": getattr(a, "description", None),
                "capabilities": _decode_list(getattr(a, "capabilities", [])),
                "tags": _decode_list(getattr(a, "tags", [])),
                "status": getattr(a, "status", "active"),
                "language": getattr(a, "language", None),
                "created_at": _iso(getattr(a, "created_at", None)),
            })
        return jsonify({"agents": items}), 200

    return _impl()


# ---------- POST /api/v1/agents ----------
@agents_bp.route("", methods=["POST"])
@agents_bp.route("/", methods=["POST"])
@limiter.limit("10/minute")
def create_agent():
    db, Agent, require_auth, require_perm, redact_dict, log_action = _imports_common()
    AgentCreateSchema, ValidationError = _imports_create()

    @require_auth
    @require_perm("agent:create")
    def _impl():
        payload = request.get_json(silent=True) or {}

        # Validate payload (marshmallow v4)
        try:
            data = AgentCreateSchema().load(payload)
        except ValidationError as e:
            return jsonify({"error": "validation_error", "details": e.messages}), 400

        # Unique name (per-org if present)
        q = db.session.query(Agent).filter(Agent.name == data["name"])
        if hasattr(Agent, "org_id") and hasattr(g, "user") and getattr(g.user, "org_id", None):
            q = q.filter(Agent.org_id == g.user.org_id)
        if q.first():
            return jsonify({"error": "duplicate_name"}), 409

        # Normalize inputs
        language = (data.get("language") or "en").strip()
        caps = data.get("capabilities") or []
        tags = data.get("tags") or []

        try:
            agent = Agent(
                name=data["name"].strip(),
                description=(data.get("description") or "").strip() or None,
                language=language,
            )
        except TypeError as te:
            return jsonify({
                "error": "model_constructor_error",
                "message": str(te),
                "hint": "Align AgentCreateSchema with Agent model required fields."
            }), 400

        # Optional columns
        if hasattr(Agent, "org_id") and hasattr(g, "user") and getattr(g.user, "org_id", None):
            agent.org_id = g.user.org_id
        if hasattr(Agent, "owner_id") and hasattr(g, "user") and getattr(g.user, "id", None):
            agent.owner_id = g.user.id
        if hasattr(Agent, "capabilities"):
            agent.capabilities = _encode_list(caps)
        if hasattr(Agent, "tags"):
            agent.tags = _encode_list(tags)
        if hasattr(Agent, "status"):
            agent.status = "active"

        db.session.add(agent)
        db.session.commit()

        # Audit (safely redacted)
        log_action("agent.created", "agent", resource_id=agent.id, metadata=redact_dict(data))

        return jsonify({
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "language": getattr(agent, "language", None),
            "capabilities": _decode_list(getattr(agent, "capabilities", [])),
            "tags": _decode_list(getattr(agent, "tags", [])),
        }), 201

    return _impl()
