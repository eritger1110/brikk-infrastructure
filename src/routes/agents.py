from flask import Blueprint, request, jsonify, g
from marshmallow import ValidationError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from ..database.db import db
from ..models.agent import Agent
from ..schemas.agent import AgentCreateSchema
from ..services.security import require_auth, require_perm, redact_dict
from ..services.audit import log_action

# IMPORTANT: url_prefix is the full path for this resource.
# In main.py we call app.register_blueprint(agents_bp) WITHOUT an extra prefix.
agents_bp = Blueprint("agents", __name__, url_prefix="/api/v1/agents")

# Limiter is initialized in main.py via agents_limiter.init_app(app)
limiter = Limiter(key_func=get_remote_address)


# ---------- GET /api/v1/agents ----------
@agents_bp.get("")
@agents_bp.get("/")
@require_auth
def list_agents():
    q = db.session.query(Agent)

    if hasattr(Agent, "deleted_at"):
        q = q.filter(Agent.deleted_at.is_(None))

    if hasattr(Agent, "created_at"):
        q = q.order_by(Agent.created_at.desc())
    else:
        q = q.order_by(Agent.id.desc())

    # org scoping if your model/user has it
    if hasattr(Agent, "org_id") and hasattr(g.user, "org_id"):
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
            "created_at": getattr(a, "created_at", None).isoformat() + "Z"
                          if getattr(a, "created_at", None) else None,
        })
    return jsonify({"agents": items}), 200


# ---------- POST /api/v1/agents ----------
@agents_bp.post("")
@agents_bp.post("/")
@require_auth
@require_perm("agent:create")
@limiter.limit("10/minute")
def create_agent():
    try:
        payload = request.get_json(silent=True) or {}
        data = AgentCreateSchema().load(payload)
    except ValidationError as e:
        return jsonify({"error": "validation_error", "details": e.messages}), 400

    # Deduplicate by name
    existing = db.session.query(Agent).filter_by(name=data["name"]).first()
    if existing:
        return jsonify({"error": "duplicate_name"}), 409

    agent = Agent(
        name=data["name"].strip(),
        description=(data.get("description") or "").strip() or None,
    )

    # Ownership / org / misc optional fields
    if hasattr(Agent, "org_id") and hasattr(g.user, "org_id"):
        agent.org_id = g.user.org_id
    if hasattr(Agent, "owner_id") and hasattr(g.user, "id"):
        agent.owner_id = g.user.id
    if hasattr(Agent, "capabilities"):
        agent.capabilities = data.get("capabilities") or []
    if hasattr(Agent, "tags"):
        agent.tags = data.get("tags") or []
    if hasattr(Agent, "status"):
        agent.status = "active"

    db.session.add(agent)
    db.session.commit()

    log_action("agent.created", "agent", resource_id=agent.id, metadata=redact_dict(data))
    return jsonify({"id": agent.id, "name": agent.name, "description": agent.description}), 201
