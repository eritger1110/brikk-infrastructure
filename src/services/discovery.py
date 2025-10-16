"""
Discovery and recommendation service for Phase 7
Handles agent search, filtering, and personalized recommendations
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, or_, and_, desc

from src.infra.db import db
from src.models.marketplace import MarketplaceListing, AgentTag, AgentInstallation
from src.models.analytics import AgentAnalyticsDaily, AgentTrendingScore
from src.models.reviews import AgentRatingSummary
from src.models.agent import Agent
from src.infra.log import get_logger

logger = get_logger(__name__)


class DiscoveryService:
    """Service for agent discovery and recommendations"""
    
    @staticmethod
    def search_agents(
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        pricing: Optional[str] = None,
        min_rating: Optional[float] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search for agents with full-text search and filtering
        
        Args:
            query: Search query string
            category: Filter by category
            tags: Filter by tags
            pricing: Filter by pricing model
            min_rating: Minimum average rating
            limit: Maximum results to return
            offset: Pagination offset
            
        Returns:
            dict: Search results with listings and metadata
        """
        try:
            # Build base query
            base_query = MarketplaceListing.query.filter_by(status='published')
            
            # Apply search query (simple text matching for now)
            # In production, use PostgreSQL full-text search or Elasticsearch
            if query:
                search_term = f"%{query}%"
                base_query = base_query.join(Agent).filter(
                    or_(
                        MarketplaceListing.short_description.ilike(search_term),
                        MarketplaceListing.long_description.ilike(search_term),
                        Agent.name.ilike(search_term),
                        Agent.description.ilike(search_term)
                    )
                )
            
            # Apply category filter
            if category:
                base_query = base_query.filter_by(category=category)
            
            # Apply tags filter
            if tags:
                for tag in tags:
                    base_query = base_query.filter(MarketplaceListing.tags.contains([tag]))
            
            # Apply pricing filter
            if pricing:
                base_query = base_query.filter_by(pricing_model=pricing)
            
            # Apply rating filter
            if min_rating:
                base_query = base_query.join(
                    AgentRatingSummary,
                    MarketplaceListing.agent_id == AgentRatingSummary.agent_id
                ).filter(AgentRatingSummary.average_rating >= min_rating)
            
            # Get total count before pagination
            total_count = base_query.count()
            
            # Apply pagination and ordering (by relevance/popularity)
            listings = base_query.order_by(
                MarketplaceListing.install_count.desc()
            ).limit(limit).offset(offset).all()
            
            # Build results with additional metadata
            results = []
            for listing in listings:
                listing_dict = listing.to_dict()
                
                # Add agent details
                if listing.agent:
                    listing_dict['agent'] = {
                        'id': listing.agent.id,
                        'name': listing.agent.name,
                        'version': listing.agent.version
                    }
                
                # Add rating
                rating = AgentRatingSummary.query.get(listing.agent_id)
                if rating:
                    listing_dict['rating'] = {
                        'average': float(rating.average_rating),
                        'total_reviews': rating.total_reviews
                    }
                
                results.append(listing_dict)
            
            return {
                'results': results,
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'query': query
            }
            
        except Exception as e:
            logger.error(f"Error searching agents: {str(e)}")
            raise
    
    @staticmethod
    def get_recommendations_for_user(
        user_id: str,
        limit: int = 10,
        exclude_installed: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get personalized agent recommendations for a user
        
        Uses collaborative filtering based on:
        - Agents installed by similar users
        - Agents in same categories as user's installed agents
        - Trending agents in user's interest areas
        
        Args:
            user_id: User ID to get recommendations for
            limit: Maximum recommendations to return
            exclude_installed: Whether to exclude already installed agents
            
        Returns:
            list: Recommended agent listings
        """
        try:
            # Get user's installed agents
            user_installations = AgentInstallation.query.filter_by(
                user_id=user_id
            ).filter(AgentInstallation.uninstalled_at == None).all()
            
            user_agent_ids = [i.agent_id for i in user_installations]
            
            if not user_agent_ids:
                # New user - return trending agents
                return DiscoveryService._get_trending_recommendations(limit)
            
            # Get categories and tags from user's installed agents
            user_listings = MarketplaceListing.query.filter(
                MarketplaceListing.agent_id.in_(user_agent_ids)
            ).all()
            
            user_categories = set(l.category for l in user_listings if l.category)
            user_tags = set()
            for listing in user_listings:
                if listing.tags:
                    user_tags.update(listing.tags)
            
            # Find similar users (users who installed same agents)
            similar_users = db.session.query(
                AgentInstallation.user_id,
                func.count(AgentInstallation.id).label('common_agents')
            ).filter(
                AgentInstallation.agent_id.in_(user_agent_ids),
                AgentInstallation.user_id != user_id,
                AgentInstallation.uninstalled_at == None
            ).group_by(AgentInstallation.user_id).order_by(
                desc('common_agents')
            ).limit(20).all()
            
            similar_user_ids = [u[0] for u in similar_users]
            
            # Get agents installed by similar users
            collaborative_recommendations = []
            if similar_user_ids:
                collaborative_recommendations = DiscoveryService._get_collaborative_recommendations(
                    similar_user_ids,
                    user_agent_ids,
                    limit // 2
                )
            
            # Get content-based recommendations (same categories/tags)
            content_recommendations = DiscoveryService._get_content_based_recommendations(
                user_categories,
                user_tags,
                user_agent_ids,
                limit // 2
            )
            
            # Combine and deduplicate recommendations
            all_recommendations = collaborative_recommendations + content_recommendations
            seen_ids = set()
            unique_recommendations = []
            
            for rec in all_recommendations:
                if rec['agent_id'] not in seen_ids:
                    seen_ids.add(rec['agent_id'])
                    unique_recommendations.append(rec)
                    
                    if len(unique_recommendations) >= limit:
                        break
            
            # If we don't have enough, fill with trending
            if len(unique_recommendations) < limit:
                trending = DiscoveryService._get_trending_recommendations(
                    limit - len(unique_recommendations),
                    exclude_ids=list(seen_ids)
                )
                unique_recommendations.extend(trending)
            
            return unique_recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations for user {user_id}: {str(e)}")
            raise
    
    @staticmethod
    def _get_collaborative_recommendations(
        similar_user_ids: List[str],
        exclude_agent_ids: List[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get recommendations based on similar users' installations"""
        try:
            # Get agents installed by similar users
            recommendations = db.session.query(
                AgentInstallation.agent_id,
                func.count(AgentInstallation.id).label('install_count')
            ).filter(
                AgentInstallation.user_id.in_(similar_user_ids),
                ~AgentInstallation.agent_id.in_(exclude_agent_ids),
                AgentInstallation.uninstalled_at == None
            ).group_by(AgentInstallation.agent_id).order_by(
                desc('install_count')
            ).limit(limit).all()
            
            # Build result with listing details
            results = []
            for agent_id, install_count in recommendations:
                listing = MarketplaceListing.query.filter_by(
                    agent_id=agent_id,
                    status='published'
                ).first()
                
                if listing:
                    listing_dict = listing.to_dict()
                    listing_dict['recommendation_score'] = install_count
                    listing_dict['recommendation_reason'] = 'popular_with_similar_users'
                    results.append(listing_dict)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting collaborative recommendations: {str(e)}")
            return []
    
    @staticmethod
    def _get_content_based_recommendations(
        categories: set,
        tags: set,
        exclude_agent_ids: List[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get recommendations based on content similarity"""
        try:
            # Build query for similar content
            query = MarketplaceListing.query.filter_by(status='published')
            
            if exclude_agent_ids:
                query = query.filter(~MarketplaceListing.agent_id.in_(exclude_agent_ids))
            
            # Filter by categories or tags
            if categories or tags:
                filters = []
                if categories:
                    filters.append(MarketplaceListing.category.in_(list(categories)))
                if tags:
                    # Match any of the user's tags
                    for tag in tags:
                        filters.append(MarketplaceListing.tags.contains([tag]))
                
                query = query.filter(or_(*filters))
            
            # Order by popularity and rating
            query = query.outerjoin(
                AgentRatingSummary,
                MarketplaceListing.agent_id == AgentRatingSummary.agent_id
            ).order_by(
                desc(AgentRatingSummary.average_rating),
                desc(MarketplaceListing.install_count)
            )
            
            listings = query.limit(limit).all()
            
            # Build results
            results = []
            for listing in listings:
                listing_dict = listing.to_dict()
                listing_dict['recommendation_reason'] = 'similar_content'
                results.append(listing_dict)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting content-based recommendations: {str(e)}")
            return []
    
    @staticmethod
    def _get_trending_recommendations(
        limit: int,
        exclude_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get trending agents as recommendations"""
        try:
            query = AgentTrendingScore.query
            
            if exclude_ids:
                query = query.filter(~AgentTrendingScore.agent_id.in_(exclude_ids))
            
            trending_scores = query.order_by(
                AgentTrendingScore.trending_score.desc()
            ).limit(limit).all()
            
            results = []
            for score in trending_scores:
                listing = MarketplaceListing.query.filter_by(
                    agent_id=score.agent_id,
                    status='published'
                ).first()
                
                if listing:
                    listing_dict = listing.to_dict()
                    listing_dict['recommendation_reason'] = 'trending'
                    listing_dict['trending_score'] = float(score.trending_score)
                    results.append(listing_dict)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting trending recommendations: {str(e)}")
            return []
    
    @staticmethod
    def get_similar_agents(agent_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find agents similar to a given agent
        
        Based on:
        - Same category
        - Shared tags
        - Similar functionality (description similarity)
        
        Args:
            agent_id: Agent ID to find similar agents for
            limit: Maximum similar agents to return
            
        Returns:
            list: Similar agent listings
        """
        try:
            # Get the source agent listing
            source_listing = MarketplaceListing.query.filter_by(
                agent_id=agent_id,
                status='published'
            ).first()
            
            if not source_listing:
                return []
            
            # Build similarity query
            query = MarketplaceListing.query.filter(
                MarketplaceListing.agent_id != agent_id,
                MarketplaceListing.status == 'published'
            )
            
            # Prefer same category
            if source_listing.category:
                query = query.filter_by(category=source_listing.category)
            
            # Match tags
            if source_listing.tags:
                # Find listings with overlapping tags
                for tag in source_listing.tags:
                    query = query.filter(MarketplaceListing.tags.contains([tag]))
            
            # Order by popularity and rating
            query = query.outerjoin(
                AgentRatingSummary,
                MarketplaceListing.agent_id == AgentRatingSummary.agent_id
            ).order_by(
                desc(AgentRatingSummary.average_rating),
                desc(MarketplaceListing.install_count)
            )
            
            similar_listings = query.limit(limit).all()
            
            # Build results
            results = []
            for listing in similar_listings:
                listing_dict = listing.to_dict()
                
                # Calculate similarity score based on shared tags
                if source_listing.tags and listing.tags:
                    shared_tags = set(source_listing.tags) & set(listing.tags)
                    similarity = len(shared_tags) / len(set(source_listing.tags) | set(listing.tags))
                else:
                    similarity = 0.5 if source_listing.category == listing.category else 0.3
                
                listing_dict['similarity_score'] = round(similarity, 2)
                results.append(listing_dict)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting similar agents for {agent_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_popular_in_category(category: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most popular agents in a category
        
        Args:
            category: Category slug
            limit: Maximum agents to return
            
        Returns:
            list: Popular agent listings in category
        """
        try:
            listings = MarketplaceListing.query.filter_by(
                category=category,
                status='published'
            ).order_by(
                MarketplaceListing.install_count.desc()
            ).limit(limit).all()
            
            results = []
            for listing in listings:
                listing_dict = listing.to_dict()
                
                # Add rating
                rating = AgentRatingSummary.query.get(listing.agent_id)
                if rating:
                    listing_dict['rating'] = {
                        'average': float(rating.average_rating),
                        'total_reviews': rating.total_reviews
                    }
                
                results.append(listing_dict)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting popular agents in category {category}: {str(e)}")
            raise
    
    @staticmethod
    def get_new_releases(days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recently published agents
        
        Args:
            days: Number of days to look back
            limit: Maximum agents to return
            
        Returns:
            list: Recently published agent listings
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            listings = MarketplaceListing.query.filter(
                MarketplaceListing.status == 'published',
                MarketplaceListing.published_at >= cutoff_date
            ).order_by(
                MarketplaceListing.published_at.desc()
            ).limit(limit).all()
            
            results = []
            for listing in listings:
                listing_dict = listing.to_dict()
                
                # Add agent details
                if listing.agent:
                    listing_dict['agent'] = {
                        'id': listing.agent.id,
                        'name': listing.agent.name,
                        'version': listing.agent.version
                    }
                
                results.append(listing_dict)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting new releases: {str(e)}")
            raise

