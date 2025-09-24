# src/routes/agents.py
from flask import Blueprint, request, jsonify, g
from marshmallow import ValidationError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from ..database.db import db
from ..models.agent import Agent
from ..schemas.agent import AgentCreateSchema
from ..services.security import require_auth, require_perm, redact_dict
from ..services.audit import log_action

# NOTE: We mount this blueprint in main.py with url_prefix="/api/v1"
# so the full paths are /api/v1/agents and /api/v1/agents/
agents_bp = Blueprint("agents", __name__, url_prefix="/api/v1/agents")

# Limiter instance; main.py calls limiter.init_app(app)
limiter = Limiter(key_func=get_remote_address)


def _iso(dt):
    try:
        return dt.isoformat() + "Z" if dt else None
    except Exception:
        return None


# ---------- GET /api/v1/agents ----------
@agents_bp.get("")
@agents_bp.get("/")
@require_auth
def list_agents():
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
            "language": getattr(a, "language", None),
            "created_at": _iso(getattr(a, "created_at", None)),
        })
    return jsonify({"agents": items}), 200


# ---------- POST /api/v1/agents ----------
@agents_bp.post("")
@agents_bp.post("/")
@require_auth
@require_perm("agent:create")
@limiter.limit("10/minute")
def create_agent():
    # Parse JSON safely
    payload = request.get_json(silent=True) or {}

    # Validate (ok if schema doesn’t yet have 'language'; we’ll default below)
    try:
        data = AgentCreateSchema().load(payload)
    except ValidationError as e:
        return jsonify({"error": "validation_error", "details": e.messages}), 400

    # Enforce unique name (per org if applicable)
    q = db.session.query(Agent).filter(Agent.name == data["name"])
    if hasattr(Agent, "org_id") and hasattr(g.user, "org_id"):
        q = q.filter(Agent.org_id == g.user.org_id)
    if q.first():
        return jsonify({"error": "duplicate_name"}), 409

    # ---- CRITICAL: Provide language (model requires it) ----
    language = data.get("language") or "en"

    try:
        agent = Agent(
            name=data["name"].strip(),
            description=(data.get("description") or "").strip() or None,
            language=language,  # required by model
        )
    except TypeError as te:
        # If the model changes again (new required args), return a 400 instead of 500
        return jsonify({
            "error": "model_constructor_error",
            "message": str(te),
            "hint": "Align AgentCreateSchema and the Agent model required fields."
        }), 400

    # Ownership / org / misc fields (only if those columns exist)
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

    # Audit (redacts sensitive keys)
    log_action("agent.created", "agent", resource_id=agent.id, metadata=redact_dict(data))

    return jsonify({
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "language": getattr(agent, "language", None)
    }), 201
