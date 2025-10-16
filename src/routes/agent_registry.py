# -*- coding: utf-8 -*-
"""
Agent Registry Routes (Phase 6).

Provides CRUD operations for the Agent Registry with ownership enforcement
and OAuth2 scope-based access control.
"""
import uuid
from flask import Blueprint, request, jsonify, g
from src.database import db
from src.models.agent import Agent
from src.models.org import Organization
from src.services.auth_middleware import require_scope
from typing import List, Optional

agent_registry_bp = Blueprint('agent_registry', __name__)


@agent_registry_bp.route('/v1/agents/register', methods=['POST'])
@require_scope('agents:write')
def register_agent():
    """
    Register a new agent in the registry.
    
    Requires: agents:write scope
    
    Request Body:
        {
            "name": "My Agent",
            "description": "Agent description",
            "category": "utility",
            "endpoint_url": "https://api.example.com/agent",
            "version": "1.0.0",
            "tags": ["search", "nlp"],
            "capabilities": {"max_tokens": 4000},
            "oauth_client_id": "optional_client_id"
        }
    """
    data = request.get_json()
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'name is required'}), 400
    if not data.get('endpoint_url'):
        return jsonify({'error': 'endpoint_url is required'}), 400
    
    # Get org_id from authenticated context
    org_id = g.org_id if hasattr(g, 'org_id') else None
    if not org_id:
        return jsonify({'error': 'Organization context required'}), 403
    
    # Create agent
    agent = Agent(
        name=data['name'],
        language=data.get('language', 'en'),  # Default language for backward compat
        organization_id=org_id,
        description=data.get('description'),
        category=data.get('category'),
        endpoint_url=data['endpoint_url'],
        version=data.get('version', '1.0.0'),
        oauth_client_id=data.get('oauth_client_id'),
        active=True
    )
    
    # Set tags and capabilities (JSON stored in TEXT)
    if data.get('tags'):
        agent.set_capabilities(data['tags'])  # Using existing method
        agent.tags = data['tags']
    
    if data.get('capabilities'):
        agent.capabilities = data['capabilities']
    
    db.session.add(agent)
    db.session.commit()
    
    return jsonify({
        'message': 'Agent registered successfully',
        'agent': agent.to_dict(include_sensitive=True)
    }), 201


@agent_registry_bp.route('/v1/agents', methods=['GET'])
@require_scope('agents:read')
def list_agents():
    """
    List agents with optional filters.
    
    Requires: agents:read scope
    
    Query Parameters:
        - q: Text search query
        - category: Filter by category
        - tag: Filter by tag (can be repeated)
        - org_id: Filter by organization (admin only)
        - active: Filter by active status (default: true)
    """
    # Get query parameters
    query = request.args.get('q')
    category = request.args.get('category')
    tags = request.args.getlist('tag')
    org_id = request.args.get('org_id')
    active_only = request.args.get('active', 'true').lower() == 'true'
    
    # Enforce org ownership unless admin
    if not org_id and hasattr(g, 'org_id'):
        org_id = g.org_id
    
    # Search agents
    agents = Agent.search(
        query=query,
        category=category,
        tags=tags if tags else None,
        org_id=org_id,
        active_only=active_only
    )
    
    return jsonify({
        'agents': [agent.to_dict() for agent in agents],
        'count': len(agents)
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
        return jsonify({'error': 'Agent not found'}), 404
    
    # Check if requester owns the agent or has admin access
    include_sensitive = False
    if hasattr(g, 'org_id') and str(agent.organization_id) == str(g.org_id):
        include_sensitive = True
    
    return jsonify({
        'agent': agent.to_dict(include_sensitive=include_sensitive)
    }), 200


@agent_registry_bp.route('/v1/agents/<agent_id>', methods=['PATCH'])
@require_scope('agents:write')
def update_agent(agent_id: str):
    """
    Update agent details.
    
    Requires: agents:write scope
    Ownership: Only the owning organization can update
    """
    agent = Agent.query.filter_by(id=agent_id).first()
    
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    # Enforce ownership
    if hasattr(g, 'org_id') and str(agent.organization_id) != str(g.org_id):
        return jsonify({'error': 'Forbidden: You do not own this agent'}), 403
    
    data = request.get_json()
    
    # Update allowed fields
    if 'name' in data:
        agent.name = data['name']
    if 'description' in data:
        agent.description = data['description']
    if 'category' in data:
        agent.category = data['category']
    if 'endpoint_url' in data:
        agent.endpoint_url = data['endpoint_url']
    if 'version' in data:
        agent.version = data['version']
    if 'tags' in data:
        agent.tags = data['tags']
    if 'capabilities' in data:
        agent.capabilities = data['capabilities']
    if 'oauth_client_id' in data:
        agent.oauth_client_id = data['oauth_client_id']
    if 'active' in data:
        agent.active = data['active']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Agent updated successfully',
        'agent': agent.to_dict(include_sensitive=True)
    }), 200


@agent_registry_bp.route('/v1/agents/<agent_id>', methods=['DELETE'])
@require_scope('agents:write')
def delete_agent(agent_id: str):
    """
    Soft delete an agent (sets active=False).
    
    Requires: agents:write scope
    Ownership: Only the owning organization can delete
    """
    agent = Agent.query.filter_by(id=agent_id).first()
    
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    # Enforce ownership
    if hasattr(g, 'org_id') and str(agent.organization_id) != str(g.org_id):
        return jsonify({'error': 'Forbidden: You do not own this agent'}), 403
    
    # Soft delete
    agent.active = False
    db.session.commit()
    
    return jsonify({
        'message': 'Agent deleted successfully',
        'agent_id': agent_id
    }), 200

