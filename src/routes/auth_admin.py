# -*- coding: utf-8 -*-
"""
Admin routes for API key management, protected by BRIKK_ADMIN_TOKEN.
"""
import os
from flask import Blueprint, request, jsonify, current_app
from functools import wraps
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from src.models.org import Organization
from src.models.agent import Agent
from src.models.api_key import ApiKey
from src.schemas.auth import (
    CreateOrganizationRequest,
    CreateAgentRequest,
    CreateApiKeyRequest,
    RotateApiKeyRequest,
    DisableApiKeyRequest,
    OrganizationResponse,
    AgentResponse,
    ApiKeyWithSecretResponse,
    ApiKeyResponse,
    AuthErrorResponse
)
from src.database import db
from src.services.security_enhanced import HMACSecurityService

# Create blueprint
auth_admin_bp = Blueprint('auth_admin', __name__, url_prefix='/internal')


def require_admin_token(f):
    """Decorator to require BRIKK_ADMIN_TOKEN for admin endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_token = os.environ.get('BRIKK_ADMIN_TOKEN')
        if not admin_token:
            return jsonify({
                'code': 'admin_not_configured',
                'message': 'Admin token not configured',
                'request_id': HMACSecurityService.generate_request_id()
            }), 500

        provided_token = request.headers.get('Authorization')
        if not provided_token:
            return jsonify({
                'code': 'admin_token_required',
                'message': 'Authorization header required',
                'request_id': HMACSecurityService.generate_request_id()
            }), 401

        # Support both "Bearer <token>" and direct token formats
        if provided_token.startswith('Bearer '):
            provided_token = provided_token[7:]

        if not HMACSecurityService.constant_time_compare(
                provided_token, admin_token):
            return jsonify({
                'code': 'invalid_admin_token',
                'message': 'Invalid admin token',
                'request_id': HMACSecurityService.generate_request_id()
            }), 401

        return f(*args, **kwargs)
    return decorated_function


@auth_admin_bp.route('/health', methods=['GET'])
def admin_health():
    """Health check for admin endpoints."""
    return jsonify({
        'status': 'healthy',
        'service': 'auth_admin',
        'admin_configured': bool(os.environ.get('BRIKK_ADMIN_TOKEN')),
        'timestamp': HMACSecurityService.generate_request_id()
    })


# Organization Management
@auth_admin_bp.route('/organizations', methods=['POST'])
@require_admin_token
def create_organization():
    """Create a new organization."""
    try:
        # Validate request
        data = CreateOrganizationRequest(**request.json)

        # Check if slug already exists
        existing_org = Organization.query.filter_by(slug=data.slug).first()
        if existing_org:
            return jsonify({
                'code': 'organization_exists',
                'message': f'Organization with slug "{data.slug}" already exists',
                'request_id': HMACSecurityService.generate_request_id()
            }), 409

        # Create organization
        org = Organization(
            name=data.name,
            slug=data.slug,
            description=data.description,
            contact_email=data.contact_email,
            contact_name=data.contact_name,
            monthly_request_limit=data.monthly_request_limit
        )

        db.session.add(org)
        db.session.commit()

        current_app.logger.info(
            f"Created organization: {org.slug} (ID: {org.id})")

        return jsonify(OrganizationResponse(**org.to_dict()).dict()), 201

    except ValidationError as e:
        return jsonify({
            'code': 'validation_error',
            'message': 'Invalid request data',
            'details': e.errors(),
            'request_id': HMACSecurityService.generate_request_id()
        }), 400
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({
            'code': 'database_error',
            'message': 'Failed to create organization due to database constraint',
            'request_id': HMACSecurityService.generate_request_id()
        }), 409
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create organization: {e}")
        return jsonify({
            'code': 'internal_error',
            'message': 'Failed to create organization',
            'request_id': HMACSecurityService.generate_request_id()
        }), 500


@auth_admin_bp.route('/organizations', methods=['GET'])
@require_admin_token
def list_organizations():
    """List all organizations."""
    try:
        organizations = Organization.query.all()
        return jsonify([OrganizationResponse(**org.to_dict()).dict()
                       for org in organizations])
    except Exception as e:
        current_app.logger.error(f"Failed to list organizations: {e}")
        return jsonify({
            'code': 'internal_error',
            'message': 'Failed to list organizations',
            'request_id': HMACSecurityService.generate_request_id()
        }), 500


@auth_admin_bp.route('/organizations/<slug>', methods=['GET'])
@require_admin_token
def get_organization(slug):
    """Get organization by slug."""
    try:
        org = Organization.get_by_slug(slug)
        if not org:
            return jsonify({
                'code': 'organization_not_found',
                'message': f'Organization "{slug}" not found',
                'request_id': HMACSecurityService.generate_request_id()
            }), 404

        return jsonify(OrganizationResponse(**org.to_dict()).dict())
    except Exception as e:
        current_app.logger.error(f"Failed to get organization: {e}")
        return jsonify({
            'code': 'internal_error',
            'message': 'Failed to get organization',
            'request_id': HMACSecurityService.generate_request_id()
        }), 500


# Agent Management
@auth_admin_bp.route('/organizations/<slug>/agents', methods=['POST'])
@require_admin_token
def create_agent(slug):
    """Create a new agent for an organization."""
    try:
        # Get organization
        org = Organization.get_by_slug(slug)
        if not org:
            return jsonify({
                'code': 'organization_not_found',
                'message': f'Organization "{slug}" not found',
                'request_id': HMACSecurityService.generate_request_id()
            }), 404

        # Validate request
        data = CreateAgentRequest(**request.json)

        # Check if agent_id already exists in this organization
        existing_agent = Agent.get_by_agent_id(data.agent_id, org.id)
        if existing_agent:
            return jsonify({
                'code': 'agent_exists',
                'message': f'Agent "{data.agent_id}" already exists in organization "{slug}"',
                'request_id': HMACSecurityService.generate_request_id()
            }), 409

        # Create agent
        agent = Agent(
            agent_id=data.agent_id,
            name=data.name,
            description=data.description,
            organization_id=org.id,
            agent_type=data.agent_type,
            capabilities=data.capabilities,
            endpoint_url=data.endpoint_url
        )

        db.session.add(agent)
        db.session.commit()

        current_app.logger.info(
            f"Created agent: {agent.agent_id} for org {org.slug}")

        return jsonify(AgentResponse(**agent.to_dict()).dict()), 201

    except ValidationError as e:
        return jsonify({
            'code': 'validation_error',
            'message': 'Invalid request data',
            'details': e.errors(),
            'request_id': HMACSecurityService.generate_request_id()
        }), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create agent: {e}")
        return jsonify({
            'code': 'internal_error',
            'message': 'Failed to create agent',
            'request_id': HMACSecurityService.generate_request_id()
        }), 500


@auth_admin_bp.route('/organizations/<slug>/agents', methods=['GET'])
@require_admin_token
def list_agents(slug):
    """List agents for an organization."""
    try:
        org = Organization.get_by_slug(slug)
        if not org:
            return jsonify({
                'code': 'organization_not_found',
                'message': f'Organization "{slug}" not found',
                'request_id': HMACSecurityService.generate_request_id()
            }), 404

        agents = Agent.get_by_organization(org.id)
        return jsonify([AgentResponse(**agent.to_dict()).dict()
                       for agent in agents])
    except Exception as e:
        current_app.logger.error(f"Failed to list agents: {e}")
        return jsonify({
            'code': 'internal_error',
            'message': 'Failed to list agents',
            'request_id': HMACSecurityService.generate_request_id()
        }), 500


# API Key Management
@auth_admin_bp.route('/keys/create', methods=['POST'])
@require_admin_token
def create_api_key():
    """Create a new API key."""
    try:
        # Validate request
        data = CreateApiKeyRequest(**request.json)

        # Get organization from request body
        org_slug = request.json.get('organization_slug')
        if not org_slug:
            return jsonify({
                'code': 'missing_organization',
                'message': 'organization_slug is required',
                'request_id': HMACSecurityService.generate_request_id()
            }), 400

        org = Organization.get_by_slug(org_slug)
        if not org:
            return jsonify({
                'code': 'organization_not_found',
                'message': f'Organization "{org_slug}" not found',
                'request_id': HMACSecurityService.generate_request_id()
            }), 404

        # Validate agent if specified
        agent = None
        if data.agent_id:
            agent = Agent.query.filter_by(
                id=data.agent_id, organization_id=org.id).first()
            if not agent:
                return jsonify({
                    'code': 'agent_not_found',
                    'message': f'Agent ID {data.agent_id} not found in organization "{org_slug}"',
                    'request_id': HMACSecurityService.generate_request_id()
                }), 404

        # Create API key
        api_key, secret = ApiKey.create_api_key(
            organization_id=org.id,
            name=data.name,
            description=data.description,
            agent_id=data.agent_id,
            expires_days=data.expires_days
        )

        # Update rate limits if specified
        if data.requests_per_minute != 100:
            api_key.requests_per_minute = data.requests_per_minute
        if data.requests_per_hour != 1000:
            api_key.requests_per_hour = data.requests_per_hour

        # Set scopes if specified
        if data.scopes:
            import json
            api_key.scopes = json.dumps(data.scopes)

        db.session.commit()

        current_app.logger.info(
            f"Created API key: {api_key.key_prefix}*** for org {org.slug}")

        # Return API key with secret (only time it's available)
        response_data = api_key.to_dict(include_secret=True)
        return jsonify(ApiKeyWithSecretResponse(**response_data).dict()), 201

    except ValidationError as e:
        return jsonify({
            'code': 'validation_error',
            'message': 'Invalid request data',
            'details': e.errors(),
            'request_id': HMACSecurityService.generate_request_id()
        }), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create API key: {e}")
        return jsonify({
            'code': 'internal_error',
            'message': 'Failed to create API key',
            'request_id': HMACSecurityService.generate_request_id()
        }), 500


@auth_admin_bp.route('/keys/rotate', methods=['POST'])
@require_admin_token
def rotate_api_key():
    """Rotate an API key secret."""
    try:
        # Validate request
        data = RotateApiKeyRequest(**request.json)

        # Get API key
        api_key = ApiKey.get_by_key_id(data.key_id)
        if not api_key:
            return jsonify({
                'code': 'api_key_not_found',
                'message': f'API key "{data.key_id}" not found',
                'request_id': HMACSecurityService.generate_request_id()
            }), 404

        # Rotate secret
        new_secret = api_key.rotate_secret()

        current_app.logger.info(f"Rotated API key: {api_key.key_prefix}***")

        # Return API key with new secret
        response_data = api_key.to_dict()
        response_data['secret'] = new_secret
        return jsonify(ApiKeyWithSecretResponse(**response_data).dict())

    except ValidationError as e:
        return jsonify({
            'code': 'validation_error',
            'message': 'Invalid request data',
            'details': e.errors(),
            'request_id': HMACSecurityService.generate_request_id()
        }), 400
    except Exception as e:
        current_app.logger.error(f"Failed to rotate API key: {e}")
        return jsonify({
            'code': 'internal_error',
            'message': 'Failed to rotate API key',
            'request_id': HMACSecurityService.generate_request_id()
        }), 500


@auth_admin_bp.route('/keys/disable', methods=['POST'])
@require_admin_token
def disable_api_key():
    """Disable an API key."""
    try:
        # Validate request
        data = DisableApiKeyRequest(**request.json)

        # Get API key
        api_key = ApiKey.get_by_key_id(data.key_id)
        if not api_key:
            return jsonify({
                'code': 'api_key_not_found',
                'message': f'API key "{data.key_id}" not found',
                'request_id': HMACSecurityService.generate_request_id()
            }), 404

        # Disable key
        api_key.disable()

        current_app.logger.info(
            f"Disabled API key: {api_key.key_prefix}*** (reason: {data.reason})")

        return jsonify(ApiKeyResponse(**api_key.to_dict()).dict())

    except ValidationError as e:
        return jsonify({
            'code': 'validation_error',
            'message': 'Invalid request data',
            'details': e.errors(),
            'request_id': HMACSecurityService.generate_request_id()
        }), 400
    except Exception as e:
        current_app.logger.error(f"Failed to disable API key: {e}")
        return jsonify({
            'code': 'internal_error',
            'message': 'Failed to disable API key',
            'request_id': HMACSecurityService.generate_request_id()
        }), 500


@auth_admin_bp.route('/keys', methods=['GET'])
@require_admin_token
def list_api_keys():
    """List all API keys (admin view)."""
    try:
        org_slug = request.args.get('organization')

        if org_slug:
            # List keys for specific organization
            org = Organization.get_by_slug(org_slug)
            if not org:
                return jsonify({
                    'code': 'organization_not_found',
                    'message': f'Organization "{org_slug}" not found',
                    'request_id': HMACSecurityService.generate_request_id()
                }), 404

            api_keys = ApiKey.get_by_organization(org.id, active_only=False)
        else:
            # List all keys
            api_keys = ApiKey.query.all()

        return jsonify([ApiKeyResponse(**key.to_dict()).dict()
                       for key in api_keys])

    except Exception as e:
        current_app.logger.error(f"Failed to list API keys: {e}")
        return jsonify({
            'code': 'internal_error',
            'message': 'Failed to list API keys',
            'request_id': HMACSecurityService.generate_request_id()
        }), 500


@auth_admin_bp.route('/keys/<key_id>', methods=['GET'])
@require_admin_token
def get_api_key(key_id):
    """Get API key details."""
    try:
        api_key = ApiKey.get_by_key_id(key_id)
        if not api_key:
            return jsonify({
                'code': 'api_key_not_found',
                'message': f'API key "{key_id}" not found',
                'request_id': HMACSecurityService.generate_request_id()
            }), 404

        return jsonify(ApiKeyResponse(**api_key.to_dict()).dict())

    except Exception as e:
        current_app.logger.error(f"Failed to get API key: {e}")
        return jsonify({
            'code': 'internal_error',
            'message': 'Failed to get API key',
            'request_id': HMACSecurityService.generate_request_id()
        }), 500
