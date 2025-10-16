"""
Analytics routes for Phase 7
Handles agent usage tracking, metrics, and dashboards
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta, date
from sqlalchemy import func, and_, or_

from src.infra.db import db
from src.models.analytics import (
    AgentUsageEvent,
    AgentAnalyticsDaily,
    UserAnalyticsDaily,
    AgentTrendingScore
)
from src.models.marketplace import MarketplaceListing, AgentInstallation
from src.models.agent import Agent
from src.utils.feature_flags import FeatureFlagManager, FeatureFlag
from src.infra.log import get_logger

logger = get_logger(__name__)
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/v1/analytics')


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def check_analytics_enabled():
    """Check if analytics feature is enabled"""
    feature_flags = FeatureFlagManager()
    if not feature_flags.is_enabled(FeatureFlag.AGENT_ANALYTICS):
        return jsonify({'error': 'analytics_disabled', 'message': 'Analytics feature is not enabled'}), 503
    return None


def get_current_user_id() -> Optional[str]:
    """Get current user ID from request context"""
    return request.headers.get('X-User-ID')


def require_auth():
    """Require authentication for protected endpoints"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'auth_required', 'message': 'Authentication required'}), 401
    return None


# =============================================================================
# USAGE EVENT TRACKING
# =============================================================================

@analytics_bp.route('/events', methods=['POST'])
def track_usage_event():
    """
    Track an agent usage event
    
    Request Body:
    - agent_id: ID of the agent
    - event_type: Type of event (invocation, error, timeout, etc.)
    - duration_ms: Duration in milliseconds
    - success: Whether the operation succeeded
    - error_message: Error message if failed
    - metadata: Additional event metadata
    """
    # Check if analytics is enabled
    error_response = check_analytics_enabled()
    if error_response:
        return error_response
    
    try:
        data = request.get_json()
        user_id = get_current_user_id()
        
        # Validate required fields
        if not data.get('agent_id'):
            return jsonify({'error': 'validation_error', 'message': 'agent_id is required'}), 400
        if not data.get('event_type'):
            return jsonify({'error': 'validation_error', 'message': 'event_type is required'}), 400
        
        # Create usage event
        event = AgentUsageEvent(
            agent_id=data['agent_id'],
            user_id=user_id,
            event_type=data['event_type'],
            duration_ms=data.get('duration_ms'),
            success=data.get('success', True),
            error_message=data.get('error_message'),
            event_metadata=data.get('metadata', {})
        )
        
        db.session.add(event)
        db.session.commit()
        
        # Update installation last_used_at if user is authenticated
        if user_id:
            installation = AgentInstallation.query.filter_by(
                agent_id=data['agent_id'],
                user_id=user_id
            ).filter(AgentInstallation.uninstalled_at == None).first()
            
            if installation:
                installation.update_last_used()
        
        logger.info(f"Usage event tracked: agent={data['agent_id']}, type={data['event_type']}")
        
        return jsonify({'message': 'Event tracked successfully', 'event_id': event.id}), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error tracking usage event: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


# =============================================================================
# AGENT ANALYTICS ENDPOINTS
# =============================================================================

@analytics_bp.route('/agents/<agent_id>', methods=['GET'])
def get_agent_analytics(agent_id: str):
    """
    Get analytics summary for an agent
    
    Query Parameters:
    - period: Time period (7d, 30d, 90d, 1y, all) - default: 30d
    """
    # Check if analytics is enabled
    error_response = check_analytics_enabled()
    if error_response:
        return error_response
    
    try:
        period = request.args.get('period', '30d')
        
        # Calculate date range
        end_date = date.today()
        if period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
        elif period == '90d':
            start_date = end_date - timedelta(days=90)
        elif period == '1y':
            start_date = end_date - timedelta(days=365)
        else:  # 'all'
            start_date = date(2020, 1, 1)  # Arbitrary old date
        
        # Get daily analytics
        daily_analytics = AgentAnalyticsDaily.query.filter(
            AgentAnalyticsDaily.agent_id == agent_id,
            AgentAnalyticsDaily.date >= start_date,
            AgentAnalyticsDaily.date <= end_date
        ).order_by(AgentAnalyticsDaily.date).all()
        
        # Calculate aggregate metrics
        total_invocations = sum(a.invocation_count for a in daily_analytics)
        total_unique_users = len(set(a.unique_users for a in daily_analytics if a.unique_users))
        total_success = sum(a.success_count for a in daily_analytics)
        total_errors = sum(a.error_count for a in daily_analytics)
        
        success_rate = (total_success / total_invocations * 100) if total_invocations > 0 else 0
        error_rate = (total_errors / total_invocations * 100) if total_invocations > 0 else 0
        
        # Calculate average performance
        avg_duration = sum(float(a.avg_duration_ms or 0) for a in daily_analytics if a.avg_duration_ms) / len(daily_analytics) if daily_analytics else 0
        
        # Get trending score
        trending = AgentTrendingScore.query.filter_by(agent_id=agent_id).first()
        
        return jsonify({
            'agent_id': agent_id,
            'period': period,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'summary': {
                'total_invocations': total_invocations,
                'unique_users': total_unique_users,
                'success_count': total_success,
                'error_count': total_errors,
                'success_rate': round(success_rate, 2),
                'error_rate': round(error_rate, 2),
                'avg_duration_ms': round(avg_duration, 2)
            },
            'trending': trending.to_dict() if trending else None,
            'daily_data': [a.to_dict() for a in daily_analytics]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting agent analytics: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@analytics_bp.route('/agents/<agent_id>/usage', methods=['GET'])
def get_agent_usage(agent_id: str):
    """
    Get detailed usage data for an agent
    
    Query Parameters:
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    - event_type: Filter by event type
    - limit: Maximum number of events to return (default: 100, max: 1000)
    """
    # Check if analytics is enabled
    error_response = check_analytics_enabled()
    if error_response:
        return error_response
    
    try:
        # Parse query parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        event_type = request.args.get('event_type')
        limit = min(int(request.args.get('limit', 100)), 1000)
        
        # Build query
        query = AgentUsageEvent.query.filter_by(agent_id=agent_id)
        
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
            query = query.filter(AgentUsageEvent.created_at >= start_date)
        
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str)
            query = query.filter(AgentUsageEvent.created_at <= end_date)
        
        if event_type:
            query = query.filter_by(event_type=event_type)
        
        # Order by most recent first
        query = query.order_by(AgentUsageEvent.created_at.desc())
        
        # Limit results
        events = query.limit(limit).all()
        
        return jsonify({
            'agent_id': agent_id,
            'events': [event.to_dict() for event in events],
            'count': len(events),
            'limit': limit
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting agent usage: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


@analytics_bp.route('/agents/<agent_id>/performance', methods=['GET'])
def get_agent_performance(agent_id: str):
    """
    Get performance metrics for an agent
    
    Query Parameters:
    - period: Time period (7d, 30d, 90d) - default: 30d
    """
    # Check if analytics is enabled
    error_response = check_analytics_enabled()
    if error_response:
        return error_response
    
    try:
        period = request.args.get('period', '30d')
        
        # Calculate date range
        end_date = date.today()
        if period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
        else:  # '90d'
            start_date = end_date - timedelta(days=90)
        
        # Get daily analytics
        daily_analytics = AgentAnalyticsDaily.query.filter(
            AgentAnalyticsDaily.agent_id == agent_id,
            AgentAnalyticsDaily.date >= start_date,
            AgentAnalyticsDaily.date <= end_date
        ).order_by(AgentAnalyticsDaily.date).all()
        
        # Calculate performance metrics
        performance_data = []
        for analytics in daily_analytics:
            performance_data.append({
                'date': analytics.date.isoformat(),
                'avg_duration_ms': float(analytics.avg_duration_ms) if analytics.avg_duration_ms else None,
                'p50_duration_ms': analytics.p50_duration_ms,
                'p95_duration_ms': analytics.p95_duration_ms,
                'p99_duration_ms': analytics.p99_duration_ms,
                'success_rate': analytics.success_rate,
                'error_rate': analytics.error_rate
            })
        
        return jsonify({
            'agent_id': agent_id,
            'period': period,
            'performance_data': performance_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting agent performance: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


# =============================================================================
# TRENDING ENDPOINTS
# =============================================================================

@analytics_bp.route('/trending', methods=['GET'])
def get_trending_agents():
    """
    Get trending agents
    
    Query Parameters:
    - limit: Maximum number of agents to return (default: 10, max: 50)
    - category: Filter by category
    """
    # Check if analytics is enabled
    error_response = check_analytics_enabled()
    if error_response:
        return error_response
    
    try:
        limit = min(int(request.args.get('limit', 10)), 50)
        category = request.args.get('category')
        
        # Build query
        query = AgentTrendingScore.query
        
        # Join with marketplace listings if category filter is specified
        if category:
            query = query.join(
                MarketplaceListing,
                AgentTrendingScore.agent_id == MarketplaceListing.agent_id
            ).filter(MarketplaceListing.category == category)
        
        # Order by trending score
        query = query.order_by(AgentTrendingScore.trending_score.desc())
        
        # Limit results
        trending_scores = query.limit(limit).all()
        
        # Build response with agent details
        result = []
        for score in trending_scores:
            score_dict = score.to_dict()
            
            # Include marketplace listing details
            listing = MarketplaceListing.query.filter_by(agent_id=score.agent_id).first()
            if listing:
                score_dict['listing'] = listing.to_dict()
            
            result.append(score_dict)
        
        return jsonify({
            'trending_agents': result,
            'count': len(result),
            'limit': limit
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting trending agents: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


# =============================================================================
# USER DASHBOARD
# =============================================================================

@analytics_bp.route('/dashboard', methods=['GET'])
def get_user_dashboard():
    """
    Get analytics dashboard for current user
    
    Query Parameters:
    - period: Time period (7d, 30d, 90d) - default: 30d
    """
    # Check if analytics is enabled
    error_response = check_analytics_enabled()
    if error_response:
        return error_response
    
    # Require authentication
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    try:
        user_id = get_current_user_id()
        period = request.args.get('period', '30d')
        
        # Calculate date range
        end_date = date.today()
        if period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
        else:  # '90d'
            start_date = end_date - timedelta(days=90)
        
        # Get user analytics
        user_analytics = UserAnalyticsDaily.query.filter(
            UserAnalyticsDaily.user_id == user_id,
            UserAnalyticsDaily.date >= start_date,
            UserAnalyticsDaily.date <= end_date
        ).order_by(UserAnalyticsDaily.date).all()
        
        # Calculate summary metrics
        total_agents_used = sum(a.agents_used for a in user_analytics)
        total_invocations = sum(a.total_invocations for a in user_analytics)
        total_active_time = sum(a.active_time_minutes for a in user_analytics)
        
        # Get installed agents
        installations = AgentInstallation.query.filter_by(
            user_id=user_id
        ).filter(AgentInstallation.uninstalled_at == None).all()
        
        installed_agents = []
        for installation in installations:
            listing = MarketplaceListing.query.filter_by(agent_id=installation.agent_id).first()
            if listing:
                installed_agents.append({
                    'installation': installation.to_dict(),
                    'listing': listing.to_dict()
                })
        
        # Get most used agents (from recent usage events)
        most_used = db.session.query(
            AgentUsageEvent.agent_id,
            func.count(AgentUsageEvent.id).label('usage_count')
        ).filter(
            AgentUsageEvent.user_id == user_id,
            AgentUsageEvent.created_at >= datetime.combine(start_date, datetime.min.time())
        ).group_by(AgentUsageEvent.agent_id).order_by(
            func.count(AgentUsageEvent.id).desc()
        ).limit(5).all()
        
        most_used_agents = []
        for agent_id, usage_count in most_used:
            listing = MarketplaceListing.query.filter_by(agent_id=agent_id).first()
            if listing:
                most_used_agents.append({
                    'agent_id': agent_id,
                    'usage_count': usage_count,
                    'listing': listing.to_dict()
                })
        
        return jsonify({
            'user_id': user_id,
            'period': period,
            'summary': {
                'total_agents_used': total_agents_used,
                'total_invocations': total_invocations,
                'total_active_time_minutes': total_active_time,
                'installed_agents_count': len(installed_agents)
            },
            'installed_agents': installed_agents,
            'most_used_agents': most_used_agents,
            'daily_activity': [a.to_dict() for a in user_analytics]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user dashboard: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500


# =============================================================================
# ANALYTICS AGGREGATION (Background Job Endpoint)
# =============================================================================

@analytics_bp.route('/aggregate/daily', methods=['POST'])
def aggregate_daily_analytics():
    """
    Aggregate daily analytics (intended to be called by background job)
    
    Request Body:
    - date: Date to aggregate (YYYY-MM-DD), defaults to yesterday
    - agent_id: Optional agent ID to aggregate specific agent
    """
    # Check if analytics is enabled
    error_response = check_analytics_enabled()
    if error_response:
        return error_response
    
    # TODO: Add admin authentication check
    
    try:
        data = request.get_json() or {}
        
        # Parse date
        if data.get('date'):
            target_date = datetime.fromisoformat(data['date']).date()
        else:
            # Default to yesterday
            target_date = date.today() - timedelta(days=1)
        
        agent_id = data.get('agent_id')
        
        # Build query for usage events
        start_datetime = datetime.combine(target_date, datetime.min.time())
        end_datetime = datetime.combine(target_date, datetime.max.time())
        
        query = AgentUsageEvent.query.filter(
            AgentUsageEvent.created_at >= start_datetime,
            AgentUsageEvent.created_at <= end_datetime
        )
        
        if agent_id:
            query = query.filter_by(agent_id=agent_id)
        
        # Get all events for the day
        events = query.all()
        
        # Group by agent
        agent_events = {}
        for event in events:
            if event.agent_id not in agent_events:
                agent_events[event.agent_id] = []
            agent_events[event.agent_id].append(event)
        
        # Aggregate for each agent
        aggregated_count = 0
        for agent_id, agent_event_list in agent_events.items():
            # Calculate metrics
            invocation_count = len(agent_event_list)
            unique_users = len(set(e.user_id for e in agent_event_list if e.user_id))
            success_count = sum(1 for e in agent_event_list if e.success)
            error_count = sum(1 for e in agent_event_list if not e.success)
            
            # Calculate duration metrics
            durations = [e.duration_ms for e in agent_event_list if e.duration_ms is not None]
            if durations:
                durations.sort()
                avg_duration = sum(durations) / len(durations)
                p50_duration = durations[len(durations) // 2]
                p95_duration = durations[int(len(durations) * 0.95)]
                p99_duration = durations[int(len(durations) * 0.99)]
            else:
                avg_duration = None
                p50_duration = None
                p95_duration = None
                p99_duration = None
            
            # Check if analytics record exists
            analytics = AgentAnalyticsDaily.query.filter_by(
                agent_id=agent_id,
                date=target_date
            ).first()
            
            if analytics:
                # Update existing record
                analytics.invocation_count = invocation_count
                analytics.unique_users = unique_users
                analytics.success_count = success_count
                analytics.error_count = error_count
                analytics.avg_duration_ms = avg_duration
                analytics.p50_duration_ms = p50_duration
                analytics.p95_duration_ms = p95_duration
                analytics.p99_duration_ms = p99_duration
            else:
                # Create new record
                analytics = AgentAnalyticsDaily(
                    agent_id=agent_id,
                    date=target_date,
                    invocation_count=invocation_count,
                    unique_users=unique_users,
                    success_count=success_count,
                    error_count=error_count,
                    avg_duration_ms=avg_duration,
                    p50_duration_ms=p50_duration,
                    p95_duration_ms=p95_duration,
                    p99_duration_ms=p99_duration
                )
                db.session.add(analytics)
            
            aggregated_count += 1
        
        db.session.commit()
        
        logger.info(f"Daily analytics aggregated for {target_date}: {aggregated_count} agents")
        
        return jsonify({
            'message': 'Analytics aggregated successfully',
            'date': target_date.isoformat(),
            'agents_aggregated': aggregated_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error aggregating daily analytics: {str(e)}")
        return jsonify({'error': 'internal_error', 'message': str(e)}), 500

