"""
Marketplace routes for Phase 7
Handles agent marketplace listing, publishing, and discovery
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.database import db
from src.models.marketplace import (
    MarketplaceListing,
    AgentCategory,
    AgentTag,
    AgentInstallation
)
from src.models.agent import Agent
from src.models.reviews import AgentRatingSummary
from src.utils.feature_flags import FeatureFlagManager, FeatureFlag
from src.infra.log import get_logger

logger = get_logger(__name__)
marketplace_bp = Blueprint('marketplace', __name__, url_prefix='/api/v1/marketplace')


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def check_marketplace_enabled():
    """Check if marketplace feature is enabled"""
    feature_flags = FeatureFlagManager()
    if not feature_flags.is_enabled(FeatureFlag.AGENT_MARKETPLACE):
        return jsonify({'error': 'marketplace_disabled', 'message': 'Marketplace feature is not enabled'}), 503
    return None


def get_current_user_id() -> Optional[str]:
    """
    Get current user ID from request context
    TODO: Implement proper authentication
    """
    # For now, return from header or None
    return request.headers.get('X-User-ID')


def require_auth():
    """Require authentication for protected endpoints"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'auth_required', 'message': 'Authentication required'}), 401
    return None


# =============================================================================
# MARKETPLACE LISTING ENDPOINTS
# =============================================================================

@marketplace_bp.route('/agents', methods=['GET'])
def list_agents():
    """
    List marketplace agents with filtering and pagination
    
    Query Parameters:
    - status: Filter by status (published, draft, archived)
    - category: Filter by category slug
    - tags: Comma-separated list of tag slugs
    - featured: Filter featured agents (true/false)
    - pricing: Filter by pricing model (free, paid, freemium)
    - sort: Sort order (popular, recent, rating, trending)
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    """
    # Check if marketplace is enabled
    error_response = check_marketplace_enabled()
    if error_response:
        return error_response
    
    try:
        # Parse query parameters
        status = request.args.get('status', 'published')
        category = request.args.get('category')
        tags = request.args.get('tags', '').split(',') if request.args.get('tags') else []
        featured = request.args.get('featured', '').lower() == 'true'
        pricing = request.args.get('pricing')
        sort = request.args.get('sort', 'popular')
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        # Build query
        query = MarketplaceListing.query
        
        # Apply filters
        if status:
            query = query.filter_by(status=status)
        
        if category:
            query = query.filter_by(category=category)
        
        if tags:
            # Filter by tags (assuming tags is a JSON array)
            for tag in tags:
                if tag:
                    query = query.filter(MarketplaceListing.tags.contains([tag]))
        
        if featured:
            query = query.filter_by(featured=True)
            query = query.filter(
                (MarketplaceListing.featured_until == None) |
                (MarketplaceListing.featured_until > datetime.now(timezone.utc))
            )
        
        if pricing:
            query = query.filter_by(pricing_model=pricing)
        
        # Apply sorting
        if sort == 'popular':
            query = query.order_by(MarketplaceListing.install_count.desc())
        elif sort == 'recent':
            query = query.order_by(MarketplaceListing.published_at.desc())
        elif sort == 'rating':
            # Join with rating summary for sorting
            query = query.outerjoin(AgentRatingSummary, MarketplaceListing.agent_id == AgentRatingSummary.agent_id)
            query = query.order_by(AgentRatingSummary.average_rating.desc().nullslast())
        elif sort == 'views':
            query = query.order_by(MarketplaceListing.view_count.desc())
        else:
            query = query.order_by(MarketplaceListing.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Build response
        listings = []
        for listing in pagination.items:
            listing_dict = listing.to_dict()
            
            # Include agent details
            if listing.agent:
                listing_dict['agent'] = {
                    'id': listing.agent.id,
                    'name': listing.agent.name,
                    'version': listing.agent.version,
                    'status': listing.agent.status,
                }
            
            # Include rating summary
            rating_summary = AgentRatingSummary.query.get(listing.agent_id)
            if rating_summary:
                listing_dict['rating'] = rating_summary.to_dict()
            
            listings.append(listing_dict)
        
        return jsonify({
            'listings': listings,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing marketplace agents: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@marketplace_bp.route('/agents/<agent_id>', methods=['GET'])
def get_agent_details(agent_id: str):
    """Get detailed information about a marketplace agent"""
    # Check if marketplace is enabled
    error_response = check_marketplace_enabled()
    if error_response:
        return error_response
    
    try:
        listing = MarketplaceListing.query.filter_by(agent_id=agent_id).first()
        
        if not listing:
            return jsonify({'error': 'not_found', 'message': 'Agent not found in marketplace'}), 404
        
        # Increment view count
        listing.increment_views()
        
        # Build detailed response
        result = listing.to_dict()
        
        # Include full agent details
        if listing.agent:
            result['agent'] = listing.agent.to_dict()
        
        # Include rating summary and recent reviews
        rating_summary = AgentRatingSummary.query.get(agent_id)
        if rating_summary:
            result['rating'] = rating_summary.to_dict()
        
        # Check if current user has installed this agent
        user_id = get_current_user_id()
        if user_id:
            installation = AgentInstallation.query.filter_by(
                agent_id=agent_id,
                user_id=user_id
            ).filter(AgentInstallation.uninstalled_at == None).first()
            result['installed'] = installation is not None
            if installation:
                result['installation'] = installation.to_dict()
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting agent details: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@marketplace_bp.route('/agents', methods=['POST'])
def publish_agent():
    """
    Publish a new agent to the marketplace
    
    Request Body:
    - agent_id: ID of the agent to publish
    - short_description: Brief description
    - long_description: Detailed description
    - category: Category slug
    - tags: List of tag slugs
    - icon_url: URL to agent icon
    - screenshots: List of screenshot URLs
    - demo_url: URL to demo
    - documentation_url: URL to documentation
    - source_code_url: URL to source code
    - license: License type
    - pricing_model: Pricing model (free, paid, freemium)
    - price_amount: Price amount (if paid)
    - price_currency: Currency code (default: USD)
    """
    # Check if marketplace is enabled
    error_response = check_marketplace_enabled()
    if error_response:
        return error_response
    
    # Require authentication
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        data = request.get_json()
        user_id = get_current_user_id()
        
        # Validate required fields
        if not data.get('agent_id'):
            return jsonify({'error': 'validation_error', 'message': 'agent_id is required'}), 400
        
        # Check if agent exists
        agent = Agent.query.get(data['agent_id'])
        if not agent:
            return jsonify({'error': 'not_found', 'message': 'Agent not found'}), 404
        
        # Check if already listed
        existing_listing = MarketplaceListing.query.filter_by(agent_id=data['agent_id']).first()
        if existing_listing:
            return jsonify({'error': 'already_exists', 'message': 'Agent already listed in marketplace'}), 409
        
        # Create listing
        listing = MarketplaceListing(
            agent_id=data['agent_id'],
            publisher_id=user_id,
            status='draft',  # Start as draft
            visibility=data.get('visibility', 'public'),
            category=data.get('category'),
            tags=data.get('tags', []),
            short_description=data.get('short_description'),
            long_description=data.get('long_description'),
            icon_url=data.get('icon_url'),
            screenshots=data.get('screenshots', []),
            demo_url=data.get('demo_url'),
            documentation_url=data.get('documentation_url'),
            source_code_url=data.get('source_code_url'),
            license=data.get('license'),
            pricing_model=data.get('pricing_model', 'free'),
            price_amount=data.get('price_amount'),
            price_currency=data.get('price_currency', 'USD'),
        )
        
        db.session.add(listing)
        db.session.commit()
        
        logger.info(f"Agent {data['agent_id']} published to marketplace by user {user_id}")
        
        return jsonify(listing.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error publishing agent: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@marketplace_bp.route('/agents/<agent_id>', methods=['PUT'])
def update_agent_listing(agent_id: str):
    """Update an existing marketplace listing"""
    # Check if marketplace is enabled
    error_response = check_marketplace_enabled()
    if error_response:
        return error_response
    
    # Require authentication
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = get_current_user_id()
        listing = MarketplaceListing.query.filter_by(agent_id=agent_id).first()
        
        if not listing:
            return jsonify({'error': 'not_found', 'message': 'Listing not found'}), 404
        
        # Check ownership
        if listing.publisher_id != user_id:
            return jsonify({'error': 'forbidden', 'message': 'You do not own this listing'}), 403
        
        # Update fields
        data = request.get_json()
        
        if 'short_description' in data:
            listing.short_description = data['short_description']
        if 'long_description' in data:
            listing.long_description = data['long_description']
        if 'category' in data:
            listing.category = data['category']
        if 'tags' in data:
            listing.tags = data['tags']
        if 'icon_url' in data:
            listing.icon_url = data['icon_url']
        if 'screenshots' in data:
            listing.screenshots = data['screenshots']
        if 'demo_url' in data:
            listing.demo_url = data['demo_url']
        if 'documentation_url' in data:
            listing.documentation_url = data['documentation_url']
        if 'source_code_url' in data:
            listing.source_code_url = data['source_code_url']
        if 'license' in data:
            listing.license = data['license']
        if 'pricing_model' in data:
            listing.pricing_model = data['pricing_model']
        if 'price_amount' in data:
            listing.price_amount = data['price_amount']
        if 'price_currency' in data:
            listing.price_currency = data['price_currency']
        
        # Handle status changes
        if 'status' in data:
            new_status = data['status']
            if new_status == 'published' and listing.status != 'published':
                listing.publish()
            elif new_status == 'archived':
                listing.archive()
            else:
                listing.status = new_status
        
        listing.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        logger.info(f"Marketplace listing {agent_id} updated by user {user_id}")
        
        return jsonify(listing.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating listing: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@marketplace_bp.route('/agents/<agent_id>', methods=['DELETE'])
def delete_agent_listing(agent_id: str):
    """Remove an agent from the marketplace"""
    # Check if marketplace is enabled
    error_response = check_marketplace_enabled()
    if error_response:
        return error_response
    
    # Require authentication
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = get_current_user_id()
        listing = MarketplaceListing.query.filter_by(agent_id=agent_id).first()
        
        if not listing:
            return jsonify({'error': 'not_found', 'message': 'Listing not found'}), 404
        
        # Check ownership
        if listing.publisher_id != user_id:
            return jsonify({'error': 'forbidden', 'message': 'You do not own this listing'}), 403
        
        db.session.delete(listing)
        db.session.commit()
        
        logger.info(f"Marketplace listing {agent_id} deleted by user {user_id}")
        
        return jsonify({'message': 'Listing deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting listing: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


# =============================================================================
# INSTALLATION ENDPOINTS
# =============================================================================

@marketplace_bp.route('/agents/<agent_id>/install', methods=['POST'])
def install_agent(agent_id: str):
    """Install an agent from the marketplace"""
    # Check if marketplace is enabled
    error_response = check_marketplace_enabled()
    if error_response:
        return error_response
    
    # Require authentication
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = get_current_user_id()
        
        # Check if agent exists in marketplace
        listing = MarketplaceListing.query.filter_by(agent_id=agent_id, status='published').first()
        if not listing:
            return jsonify({'error': 'not_found', 'message': 'Agent not found in marketplace'}), 404
        
        # Check if already installed
        existing = AgentInstallation.query.filter_by(
            agent_id=agent_id,
            user_id=user_id
        ).filter(AgentInstallation.uninstalled_at == None).first()
        
        if existing:
            return jsonify({'error': 'already_installed', 'message': 'Agent already installed'}), 409
        
        # Create installation record
        installation = AgentInstallation(
            agent_id=agent_id,
            user_id=user_id,
            installed_version=listing.agent.version if listing.agent else None
        )
        
        db.session.add(installation)
        
        # Increment install count
        listing.increment_installs()
        
        db.session.commit()
        
        logger.info(f"Agent {agent_id} installed by user {user_id}")
        
        return jsonify(installation.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error installing agent: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@marketplace_bp.route('/agents/<agent_id>/install', methods=['DELETE'])
def uninstall_agent(agent_id: str):
    """Uninstall an agent"""
    # Check if marketplace is enabled
    error_response = check_marketplace_enabled()
    if error_response:
        return error_response
    
    # Require authentication
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = get_current_user_id()
        
        installation = AgentInstallation.query.filter_by(
            agent_id=agent_id,
            user_id=user_id
        ).filter(AgentInstallation.uninstalled_at == None).first()
        
        if not installation:
            return jsonify({'error': 'not_found', 'message': 'Agent not installed'}), 404
        
        installation.uninstall()
        
        logger.info(f"Agent {agent_id} uninstalled by user {user_id}")
        
        return jsonify({'message': 'Agent uninstalled successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error uninstalling agent: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@marketplace_bp.route('/installed', methods=['GET'])
def get_installed_agents():
    """Get list of agents installed by current user"""
    # Check if marketplace is enabled
    error_response = check_marketplace_enabled()
    if error_response:
        return error_response
    
    # Require authentication
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = get_current_user_id()
        
        installations = AgentInstallation.query.filter_by(
            user_id=user_id
        ).filter(AgentInstallation.uninstalled_at == None).all()
        
        result = []
        for installation in installations:
            install_dict = installation.to_dict()
            
            # Include listing details
            listing = MarketplaceListing.query.filter_by(agent_id=installation.agent_id).first()
            if listing:
                install_dict['listing'] = listing.to_dict()
            
            result.append(install_dict)
        
        return jsonify({'installations': result}), 200
        
    except Exception as e:
        logger.error(f"Error getting installed agents: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


# =============================================================================
# CATEGORY AND TAG ENDPOINTS
# =============================================================================

@marketplace_bp.route('/categories', methods=['GET'])
def list_categories():
    """List all agent categories"""
    try:
        categories = AgentCategory.query.order_by(AgentCategory.display_order).all()
        return jsonify({'categories': [cat.to_dict() for cat in categories]}), 200
    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@marketplace_bp.route('/tags', methods=['GET'])
def list_tags():
    """List popular tags"""
    try:
        limit = min(int(request.args.get('limit', 50)), 100)
        tags = AgentTag.query.order_by(AgentTag.usage_count.desc()).limit(limit).all()
        return jsonify({'tags': [tag.to_dict() for tag in tags]}), 200
    except Exception as e:
        logger.error(f"Error listing tags: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@marketplace_bp.route('/featured', methods=['GET'])
def get_featured_agents():
    """Get featured agents"""
    try:
        listings = MarketplaceListing.query.filter_by(
            status='published',
            featured=True
        ).filter(
            (MarketplaceListing.featured_until == None) |
            (MarketplaceListing.featured_until > datetime.now(timezone.utc))
        ).order_by(MarketplaceListing.view_count.desc()).limit(10).all()
        
        return jsonify({'listings': [listing.to_dict() for listing in listings]}), 200
    except Exception as e:
        logger.error(f"Error getting featured agents: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500

