# src/routes/agents.py
"""
Agents endpoints.

Design goals for reliability:
- Keep blueprint import side-effect free so main.py can always register it.
- Lazy import db/models/schemas INSIDE handlers to avoid import-time failures.
- Bind BOTH "" and "/" for GET/POST to avoid 301/405 on trailing slash.
- Include OPTIONS in @route methods so preflight is satisfied automatically.
"""

from flask import Blueprint, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Exported limiter object; main.py calls limiter.init_app(app)
limiter = Limiter(key_func=get_remote_address)

# IMPORTANT: This blueprint includes the full prefix.
# In main.py: app.register_blueprint(agents_bp)  (no extra url_prefix)
agents_bp = Blueprint("agents_bp", __name__, url_prefix="/api/v1/agents")


def _iso(dt):
    try:
        return dt.isoformat() + "Z" if dt else None
    except Exception:
        return None


def _safe_get_db_objects():
    """
    Lazy import of heavy modules.
    Returns (db, Agent, AgentCreateSchema, redact_dict, require_auth, require_perm, log_action)
    or raises the underlying ImportError/AttributeError for better logs.
    """
    # Local imports to avoid import-time failures blocking blueprint registration
    from src.database.db import db
    from src.models.agent import Agent
    from src.schemas.agent import AgentCreateSchema
    from src.services.security import require_auth, require_perm, redact_dict
    from src.services.audit import log_action
    return db, Agent, AgentCreateSchema, redact_dict, require_auth, require_perm, log_action


# ---------- GET /api/v1/agents ----------
@agents_bp.route("", methods=["GET", "OPTIONS"])
@agents_bp.route("/", methods=["GET", "OPTIONS"])
def list_agents():
    # bring in dependencies lazily
    db, Agent, _, _, require_auth, _, _ = _safe_get_db_objects()

    # auth (explicit call here since decorator is imported lazily)
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
                "capabilities": getattr(a, "capabilities", []) or [],
                "tags": getattr(a, "tags", []) or [],
                "status": getattr(a, "status", "active"),
                "language": getattr(a, "language", None),
                "created_at": _iso(getattr(a, "created_at", None)),
            })
        return jsonify({"agents": items}), 200

    return _impl()


# ---------- POST /api/v1/agents ----------
@agents_bp.route("", methods=["POST", "OPTIONS"])
@agents_bp.route("/", methods=["POST", "OPTIONS"])
@limiter.limit("10/minute")
def create_agent():
    db, Agent, AgentCreateSchema, redact_dict, require_auth, require_perm, log_action = _safe_get_db_objects()

    # auth + permission (explicit wrappers so we can lazy-import)
    @require_auth
    @require_perm("agent:create")
    def _impl():
        from marshmallow import ValidationError

        payload = request.get_json(silent=True) or {}

        # Validate payload
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

        language = (data.get("language") or "en").strip()

        try:
            agent = Agent(
                name=data["name"].strip(),
                description=(data.get("description") or "").strip() or None,
                language=language,
            )
        except TypeError as te:
            # If the model signature changes, surface a helpful 400
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
            agent.capabilities = data.get("capabilities") or []
        if hasattr(Agent, "tags"):
            agent.tags = data.get("tags") or []
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
            "language": getattr(agent, "language", None)
        }), 201

    return _impl()
