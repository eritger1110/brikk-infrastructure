# -*- coding: utf-8 -*-
"""
Agent Registry Routes (Phase 6 PR-I).

Provides CRUD operations for the Agent Registry with:
- Proper request validation using Marshmallow schemas
- Consistent error responses with request_id
- Ownership enforcement and OAuth2 scope-based access control
- Pagination support
"""
from flask import Blueprint, request, jsonify, g
from marshmallow import ValidationError
from src.database import db
from src.models.agent import Agent
from src.models.org import Organization
from src.infra.auth import require_scope
from src.schemas.agent_schemas import (
    AgentCreateSchema,
    AgentUpdateSchema,
    AgentResponseSchema,
    AgentListResponseSchema,
    ErrorResponseSchema
)
from src.models.trust import ReputationSnapshot
from src.services.reputation_engine import ReputationEngine
from sqlalchemy import desc

agent_registry_bp = Blueprint('agent_registry', __name__, url_prefix='/api')


def error_response(error: str, message: str, status_code: int = 400, details: dict = None):
    """Generate consistent error response with request_id."""
    response = {
        'error': error,
        'message': message,
        'request_id': getattr(g, 'request_id', None)
    }
    if details:
        response['details'] = details
    return jsonify(response), status_code


@agent_registry_bp.route('/v1/agents', methods=['POST'])
@require_scope('agents:write')
def create_agent():
    """
    Create a new agent in the registry.
    
    Requires: agents:write scope
    """
    # Get org_id from authenticated context
    org_id = getattr(g, 'org_id', None)
    if not org_id:
        return error_response('forbidden', 'Organization context required', 403)
    
    # Validate request body
    schema = AgentCreateSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as err:
        return error_response('validation_error', 'Invalid request data', 400, err.messages)
    
    # Create agent
    agent = Agent(
        name=data['name'],
        description=data['description'],
        category=data['category'],
        capabilities=data.get('capabilities', []),
        oauth_client_id=data.get('oauth_client_id'),
        organization_id=org_id,
        active=True
    )
    
    db.session.add(agent)
    db.session.commit()
    
    # Serialize response
    response_schema = AgentResponseSchema()
    return jsonify(response_schema.dump(agent)), 201


@agent_registry_bp.route('/v1/agents', methods=['GET'])
@require_scope('agents:read')
def list_agents():
    """
    List agents with optional filters and pagination.
    
    Requires: agents:read scope
    
    Query Parameters:
        - search: Text search query (searches name and description)
        - category: Filter by category
        - sort: Sort order (reputation|recency|name, default: reputation)
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20, max: 100)
    """
    # Get query parameters
    search = request.args.get('search')
    category = request.args.get('category')
    sort = request.args.get('sort', 'reputation')
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)
    
    # Enforce org ownership
    org_id = getattr(g, 'org_id', None)
    if not org_id:
        return error_response('forbidden', 'Organization context required', 403)
    
    # Build query
    query = Agent.query.filter_by(organization_id=org_id, active=True)
    
    if search:
        search_filter = f'%{search}%'
        query = query.filter(
            db.or_(
                Agent.name.ilike(search_filter),
                Agent.description.ilike(search_filter)
            )
        )
    
    if category:
        query = query.filter_by(category=category)
    
    # Apply sorting
    if sort == 'reputation':
        # Join with reputation_snapshots and sort by score DESC
        query = query.outerjoin(
            ReputationSnapshot,
            db.and_(
                ReputationSnapshot.subject_type == 'agent',
                ReputationSnapshot.subject_id == Agent.id,
                ReputationSnapshot.window_days == 30
            )
        ).order_by(desc(ReputationSnapshot.score).nullslast(), desc(Agent.created_at))
    elif sort == 'recency':
        query = query.order_by(desc(Agent.created_at))
    elif sort == 'name':
        query = query.order_by(Agent.name.asc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Serialize response with reputation enrichment
    response_schema = AgentResponseSchema(many=True)
    agents_data = response_schema.dump(pagination.items)
    
    # Enrich with reputation score buckets
    for agent_data, agent in zip(agents_data, pagination.items):
        snapshot = ReputationSnapshot.get_latest('agent', agent.id, 30)
        agent_data['reputation_score_bucket'] = ReputationEngine.bucket_score(snapshot.score) if snapshot else None
    
    return jsonify({
        'agents': agents_data,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'sort': sort
    }), 200


@agent_registry_bp.route('/v1/agents/<agent_id>', methods=['GET'])
@require_scope('agents:read')
def get_agent(agent_id: str):
    """
    Get agent details by ID.
    
    Requires: agents:read scope
    """
    agent = Agent.query.filter_by(id=agent_id).first()
    
    if not agent:
        return error_response('not_found', 'Agent not found', 404)
    
    # Check ownership
    org_id = getattr(g, 'org_id', None)
    if agent.organization_id != org_id:
        return error_response('forbidden', 'You do not have access to this agent', 403)
    
    # Serialize response
    response_schema = AgentResponseSchema()
    return jsonify(response_schema.dump(agent)), 200


@agent_registry_bp.route('/v1/agents/<agent_id>', methods=['PUT'])
@require_scope('agents:write')
def update_agent(agent_id: str):
    """
    Update agent details.
    
    Requires: agents:write scope
    Ownership: Only the owning organization can update
    """
    agent = Agent.query.filter_by(id=agent_id).first()
    
    if not agent:
        return error_response('not_found', 'Agent not found', 404)
    
    # Enforce ownership
    org_id = getattr(g, 'org_id', None)
    if agent.organization_id != org_id:
        return error_response('forbidden', 'You do not own this agent', 403)
    
    # Validate request body
    schema = AgentUpdateSchema()
    try:
        data = schema.load(request.get_json() or {})
    except ValidationError as err:
        return error_response('validation_error', 'Invalid request data', 400, err.messages)
    
    # Update fields
    for field in ['name', 'description', 'category', 'capabilities', 'active']:
        if field in data:
            setattr(agent, field, data[field])
    
    db.session.commit()
    
    # Serialize response
    response_schema = AgentResponseSchema()
    return jsonify(response_schema.dump(agent)), 200


@agent_registry_bp.route('/v1/agents/<agent_id>', methods=['DELETE'])
@require_scope('agents:write')
def delete_agent(agent_id: str):
    """
    Delete an agent (soft delete by setting active=False).
    
    Requires: agents:write scope
    Ownership: Only the owning organization can delete
    """
    agent = Agent.query.filter_by(id=agent_id).first()
    
    if not agent:
        return error_response('not_found', 'Agent not found', 404)
    
    # Enforce ownership
    org_id = getattr(g, 'org_id', None)
    if agent.organization_id != org_id:
        return error_response('forbidden', 'You do not own this agent', 403)
    
    # Soft delete
    agent.active = False
    db.session.commit()
    
    return '', 204

