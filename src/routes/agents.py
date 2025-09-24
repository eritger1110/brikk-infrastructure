from flask import Blueprint, request, jsonify, g
from marshmallow import ValidationError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from ..database.db import db
from ..models.agent import Agent
from ..schemas.agent import AgentCreateSchema
from ..services.security import require_auth, require_perm, redact_dict
from ..services.audit import log_action

# NOTE:
# - Keep the url_prefix here so the final path is /api/v1/agents/
# - Using "/" in @route() avoids the 405 you were seeing with "".
agents_bp = Blueprint("agents_bp", __name__, url_prefix="/api/v1/agents")

# Limiter instance; ensure limiter.init_app(app) is called in your app factory.
limiter = Limiter(key_func=get_remote_address)


@agents_bp.route("/", methods=["GET", "OPTIONS"])
@require_auth
def list_agents():
    """Return up to 200 most-recent agents (scoped to org if present)."""
    q = db.session.query(Agent)

    # soft-delete guard (if model has it)
    if hasattr(Agent, "deleted_at"):
        q = q.filter(Agent.deleted_at.is_(None))

    # ordering
    if hasattr(Agent, "created_at"):
        q = q.order_by(Agent.created_at.desc())
    else:
        q = q.order_by(Agent.id.desc())

    # org scoping (if both model and user have org_id)
    if hasattr(Agent, "org_id") and hasattr(g, "user") and hasattr(g.user, "org_id"):
        q = q.filter(Agent.org_id == g.user.org_id)

    items = []
    for a in q.limit(200).all():
        created = getattr(a, "created_at", None)
        items.append(
            {
                "id": a.id,
                "name": a.name,
                "description": getattr(a, "description", None),
                "capabilities": getattr(a, "capabilities", []) or [],
                "tags": getattr(a, "tags", []) or [],
                "status": getattr(a, "status", "active"),
                "created_at": (created.isoformat() + "Z") if created else None,
            }
        )

    return jsonify({"agents": items}), 200


@agents_bp.route("/", methods=["POST", "OPTIONS"])
@require_auth
@require_perm("agent:create")
@limiter.limit("10/minute")
def create_agent():
    """Create a new agent."""
    try:
        payload = request.get_json(silent=True) or {}
        data = AgentCreateSchema().load(payload)
    except ValidationError as e:
        return jsonify({"error": "validation_error", "details": e.messages}), 400

    # simple uniqueness on name within org (if present)
    q = db.session.query(Agent).filter(Agent.name == data["name"].strip())
    if hasattr(Agent, "org_id") and hasattr(g, "user") and hasattr(g.user, "org_id"):
        q = q.filter(Agent.org_id == g.user.org_id)

    if q.first():
        return jsonify({"error": "duplicate_name"}), 409

    agent = Agent(
        name=data["name"].strip(),
        description=(data.get("description") or "").strip() or None,
    )

    # ownership / org scoping if fields exist
    if hasattr(Agent, "org_id") and hasattr(g, "user") and hasattr(g.user, "org_id"):
        agent.org_id = g.user.org_id
    if hasattr(Agent, "owner_id") and hasattr(g, "user") and hasattr(g.user, "id"):
        agent.owner_id = g.user.id

    # optional fields
    if hasattr(Agent, "capabilities"):
        agent.capabilities = data.get("capabilities") or []
    if hasattr(Agent, "tags"):
        agent.tags = data.get("tags") or []
    if hasattr(Agent, "status"):
        agent.status = "active"

    db.session.add(agent)
    db.session.commit()

    # audit (redact anything sensitive in request)
    log_action(
        "agent.created",
        "agent",
        resource_id=agent.id,
        metadata=redact_dict(data),
    )

    return (
        jsonify(
            {"id": agent.id, "name": agent.name, "description": agent.description}
        ),
        201,
    )
