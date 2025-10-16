"""
Agent Discovery routes for Phase 7
Handles agent search, recommendations, and discovery features
"""
from flask import Blueprint, request, jsonify
from typing import Optional

from src.services.discovery import DiscoveryService
from src.utils.feature_flags import FeatureFlagManager, FeatureFlag
from src.infra.log import get_logger

logger = get_logger(__name__)
agent_discovery_bp = Blueprint('agent_discovery', __name__, url_prefix='/api/v1/agent-discovery')


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def check_discovery_enabled():
    """Check if discovery feature is enabled"""
    feature_flags = FeatureFlagManager()
    if not feature_flags.is_enabled(FeatureFlag.ENHANCED_DISCOVERY):
        return jsonify({'error': 'discovery_disabled', 'message': 'Discovery feature is not enabled'}), 503
    return None


def get_current_user_id() -> Optional[str]:
    """Get current user ID from request context"""
    return request.headers.get('X-User-ID')


# =============================================================================
# SEARCH ENDPOINTS
# =============================================================================

@agent_discovery_bp.route('/search', methods=['GET'])
def search_agents():
    """
    Search for agents with advanced filtering
    
    Query Parameters:
    - q: Search query
    - category: Filter by category
    - tags: Comma-separated list of tags
    - pricing: Filter by pricing model (free, paid, freemium)
    - min_rating: Minimum average rating (1-5)
    - limit: Results per page (default: 20, max: 100)
    - offset: Pagination offset (default: 0)
    """
    # Check if discovery is enabled
    error_response = check_discovery_enabled()
    if error_response:
        return error_response
    
    try:
        # Parse query parameters
        query = request.args.get('q', '')
        category = request.args.get('category')
        tags_str = request.args.get('tags', '')
        tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else None
        pricing = request.args.get('pricing')
        min_rating_str = request.args.get('min_rating')
        min_rating = float(min_rating_str) if min_rating_str else None
        limit = min(int(request.args.get('limit', 20)), 100)
        offset = int(request.args.get('offset', 0))
        
        # Perform search
        results = DiscoveryService.search_agents(
            query=query,
            category=category,
            tags=tags,
            pricing=pricing,
            min_rating=min_rating,
            limit=limit,
            offset=offset
        )
        
        return jsonify(results), 200
        
    except Exception as e:
        logger.error(f"Error searching agents: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


# =============================================================================
# RECOMMENDATION ENDPOINTS
# =============================================================================

@agent_discovery_bp.route('/recommendations', methods=['GET'])
def get_recommendations():
    """
    Get personalized agent recommendations for current user
    
    Query Parameters:
    - limit: Maximum recommendations (default: 10, max: 50)
    - exclude_installed: Exclude already installed agents (default: true)
    """
    # Check if discovery is enabled
    error_response = check_discovery_enabled()
    if error_response:
        return error_response
    
    try:
        user_id = get_current_user_id()
        
        if not user_id:
            # Anonymous user - return trending agents
            limit = min(int(request.args.get('limit', 10)), 50)
            recommendations = DiscoveryService._get_trending_recommendations(limit)
            
            return jsonify({
                'recommendations': recommendations,
                'personalized': False,
                'reason': 'Not authenticated - showing trending agents'
            }), 200
        
        # Get parameters
        limit = min(int(request.args.get('limit', 10)), 50)
        exclude_installed = request.args.get('exclude_installed', 'true').lower() == 'true'
        
        # Get personalized recommendations
        recommendations = DiscoveryService.get_recommendations_for_user(
            user_id=user_id,
            limit=limit,
            exclude_installed=exclude_installed
        )
        
        return jsonify({
            'recommendations': recommendations,
            'personalized': True,
            'user_id': user_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@agent_discovery_bp.route('/similar/<agent_id>', methods=['GET'])
def get_similar_agents(agent_id: str):
    """
    Get agents similar to a specific agent
    
    Query Parameters:
    - limit: Maximum similar agents (default: 5, max: 20)
    """
    # Check if discovery is enabled
    error_response = check_discovery_enabled()
    if error_response:
        return error_response
    
    try:
        limit = min(int(request.args.get('limit', 5)), 20)
        
        similar_agents = DiscoveryService.get_similar_agents(
            agent_id=agent_id,
            limit=limit
        )
        
        return jsonify({
            'agent_id': agent_id,
            'similar_agents': similar_agents,
            'count': len(similar_agents)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting similar agents: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


# =============================================================================
# CURATED COLLECTIONS
# =============================================================================

@agent_discovery_bp.route('/popular/<category>', methods=['GET'])
def get_popular_in_category(category: str):
    """
    Get most popular agents in a category
    
    Query Parameters:
    - limit: Maximum agents (default: 10, max: 50)
    """
    # Check if discovery is enabled
    error_response = check_discovery_enabled()
    if error_response:
        return error_response
    
    try:
        limit = min(int(request.args.get('limit', 10)), 50)
        
        popular_agents = DiscoveryService.get_popular_in_category(
            category=category,
            limit=limit
        )
        
        return jsonify({
            'category': category,
            'popular_agents': popular_agents,
            'count': len(popular_agents)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting popular agents in category: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@agent_discovery_bp.route('/new-releases', methods=['GET'])
def get_new_releases():
    """
    Get recently published agents
    
    Query Parameters:
    - days: Number of days to look back (default: 30, max: 90)
    - limit: Maximum agents (default: 10, max: 50)
    """
    # Check if discovery is enabled
    error_response = check_discovery_enabled()
    if error_response:
        return error_response
    
    try:
        days = min(int(request.args.get('days', 30)), 90)
        limit = min(int(request.args.get('limit', 10)), 50)
        
        new_releases = DiscoveryService.get_new_releases(
            days=days,
            limit=limit
        )
        
        return jsonify({
            'new_releases': new_releases,
            'days': days,
            'count': len(new_releases)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting new releases: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@agent_discovery_bp.route('/collections', methods=['GET'])
def get_collections():
    """
    Get curated collections of agents
    
    Returns predefined collections like:
    - Trending Now
    - New & Noteworthy
    - Staff Picks
    - Most Popular
    """
    # Check if discovery is enabled
    error_response = check_discovery_enabled()
    if error_response:
        return error_response
    
    try:
        collections = []
        
        # Trending Now
        trending = DiscoveryService._get_trending_recommendations(limit=10)
        if trending:
            collections.append({
                'id': 'trending',
                'title': 'Trending Now',
                'description': 'Agents gaining popularity right now',
                'agents': trending
            })
        
        # New & Noteworthy
        new_releases = DiscoveryService.get_new_releases(days=14, limit=10)
        if new_releases:
            collections.append({
                'id': 'new-noteworthy',
                'title': 'New & Noteworthy',
                'description': 'Recently published agents worth checking out',
                'agents': new_releases
            })
        
        # Most Popular (all-time)
        from src.models.marketplace import MarketplaceListing
        popular = MarketplaceListing.query.filter_by(
            status='published'
        ).order_by(
            MarketplaceListing.install_count.desc()
        ).limit(10).all()
        
        if popular:
            collections.append({
                'id': 'most-popular',
                'title': 'Most Popular',
                'description': 'All-time most installed agents',
                'agents': [p.to_dict() for p in popular]
            })
        
        return jsonify({
            'collections': collections,
            'count': len(collections)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting collections: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500

