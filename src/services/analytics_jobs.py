"""
Background jobs for analytics processing
Handles daily aggregation and trending score calculation
"""
from datetime import datetime, timezone, timedelta, date
from typing import Optional
from decimal import Decimal

from src.infra.db import db
from src.models.analytics import (
    AgentUsageEvent,
    AgentAnalyticsDaily,
    UserAnalyticsDaily,
    AgentTrendingScore
)
from src.models.marketplace import MarketplaceListing
from src.infra.log import get_logger

logger = get_logger(__name__)


class AnalyticsJobService:
    """Service for running analytics background jobs"""
    
    @staticmethod
    def aggregate_daily_analytics(target_date: Optional[date] = None) -> dict:
        """
        Aggregate usage events into daily analytics
        
        Args:
            target_date: Date to aggregate (defaults to yesterday)
            
        Returns:
            dict: Summary of aggregation results
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)
        
        logger.info(f"Starting daily analytics aggregation for {target_date}")
        
        try:
            # Build datetime range
            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = datetime.combine(target_date, datetime.max.time())
            
            # Get all events for the day
            events = AgentUsageEvent.query.filter(
                AgentUsageEvent.created_at >= start_datetime,
                AgentUsageEvent.created_at <= end_datetime
            ).all()
            
            logger.info(f"Found {len(events)} events for {target_date}")
            
            # Group events by agent
            agent_events = {}
            user_events = {}
            
            for event in events:
                # Group by agent
                if event.agent_id not in agent_events:
                    agent_events[event.agent_id] = []
                agent_events[event.agent_id].append(event)
                
                # Group by user
                if event.user_id:
                    if event.user_id not in user_events:
                        user_events[event.user_id] = []
                    user_events[event.user_id].append(event)
            
            # Aggregate agent analytics
            agents_aggregated = AnalyticsJobService._aggregate_agent_analytics(
                agent_events, target_date
            )
            
            # Aggregate user analytics
            users_aggregated = AnalyticsJobService._aggregate_user_analytics(
                user_events, target_date
            )
            
            db.session.commit()
            
            result = {
                'date': target_date.isoformat(),
                'total_events': len(events),
                'agents_aggregated': agents_aggregated,
                'users_aggregated': users_aggregated
            }
            
            logger.info(f"Daily analytics aggregation completed: {result}")
            return result
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error aggregating daily analytics: {str(e)}")
            raise
    
    @staticmethod
    def _aggregate_agent_analytics(agent_events: dict, target_date: date) -> int:
        """Aggregate analytics for agents"""
        count = 0
        
        for agent_id, events in agent_events.items():
            # Calculate metrics
            invocation_count = len(events)
            unique_users = len(set(e.user_id for e in events if e.user_id))
            success_count = sum(1 for e in events if e.success)
            error_count = sum(1 for e in events if not e.success)
            
            # Calculate duration metrics
            durations = [e.duration_ms for e in events if e.duration_ms is not None]
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
            
            # Check if record exists
            analytics = AgentAnalyticsDaily.query.filter_by(
                agent_id=agent_id,
                date=target_date
            ).first()
            
            if analytics:
                # Update existing
                analytics.invocation_count = invocation_count
                analytics.unique_users = unique_users
                analytics.success_count = success_count
                analytics.error_count = error_count
                analytics.avg_duration_ms = avg_duration
                analytics.p50_duration_ms = p50_duration
                analytics.p95_duration_ms = p95_duration
                analytics.p99_duration_ms = p99_duration
                analytics.updated_at = datetime.now(timezone.utc)
            else:
                # Create new
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
            
            count += 1
        
        return count
    
    @staticmethod
    def _aggregate_user_analytics(user_events: dict, target_date: date) -> int:
        """Aggregate analytics for users"""
        count = 0
        
        for user_id, events in user_events.items():
            # Calculate metrics
            agents_used = len(set(e.agent_id for e in events))
            total_invocations = len(events)
            
            # Calculate active time (sum of durations)
            total_duration_ms = sum(e.duration_ms for e in events if e.duration_ms is not None)
            active_time_minutes = total_duration_ms / 60000 if total_duration_ms else 0
            
            # Check if record exists
            analytics = UserAnalyticsDaily.query.filter_by(
                user_id=user_id,
                date=target_date
            ).first()
            
            if analytics:
                # Update existing
                analytics.agents_used = agents_used
                analytics.total_invocations = total_invocations
                analytics.active_time_minutes = int(active_time_minutes)
                analytics.updated_at = datetime.now(timezone.utc)
            else:
                # Create new
                analytics = UserAnalyticsDaily(
                    user_id=user_id,
                    date=target_date,
                    agents_used=agents_used,
                    total_invocations=total_invocations,
                    active_time_minutes=int(active_time_minutes)
                )
                db.session.add(analytics)
            
            count += 1
        
        return count
    
    @staticmethod
    def calculate_trending_scores() -> dict:
        """
        Calculate trending scores for all agents
        
        Uses a weighted formula considering:
        - Recent growth in usage
        - Recent growth in installs
        - Recency of activity
        - Current popularity
        
        Returns:
            dict: Summary of calculation results
        """
        logger.info("Starting trending score calculation")
        
        try:
            # Get all published agents
            listings = MarketplaceListing.query.filter_by(status='published').all()
            
            scores_calculated = 0
            
            for listing in listings:
                score = AnalyticsJobService._calculate_agent_trending_score(listing.agent_id)
                
                if score is not None:
                    # Update or create trending score record
                    trending = AgentTrendingScore.query.filter_by(agent_id=listing.agent_id).first()
                    
                    if trending:
                        trending.update_score(
                            trending_score=score['trending_score'],
                            velocity=score['velocity'],
                            momentum=score['momentum']
                        )
                    else:
                        trending = AgentTrendingScore(
                            agent_id=listing.agent_id,
                            trending_score=score['trending_score'],
                            velocity=score['velocity'],
                            momentum=score['momentum'],
                            rank=0  # Will be updated in ranking step
                        )
                        db.session.add(trending)
                    
                    scores_calculated += 1
            
            # Commit all score updates
            db.session.commit()
            
            # Update rankings
            AnalyticsJobService._update_trending_rankings()
            
            result = {
                'scores_calculated': scores_calculated,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Trending score calculation completed: {result}")
            return result
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error calculating trending scores: {str(e)}")
            raise
    
    @staticmethod
    def _calculate_agent_trending_score(agent_id: str) -> Optional[dict]:
        """
        Calculate trending score for a single agent
        
        Formula:
        - Velocity: Growth rate over last 7 days vs previous 7 days
        - Momentum: Acceleration of growth
        - Recency: Boost for recent activity
        - Popularity: Base score from current metrics
        
        Trending Score = (Velocity * 0.4) + (Momentum * 0.3) + (Recency * 0.2) + (Popularity * 0.1)
        """
        try:
            today = date.today()
            
            # Get analytics for last 14 days
            last_14_days = AgentAnalyticsDaily.query.filter(
                AgentAnalyticsDaily.agent_id == agent_id,
                AgentAnalyticsDaily.date >= today - timedelta(days=14),
                AgentAnalyticsDaily.date < today
            ).order_by(AgentAnalyticsDaily.date).all()
            
            if len(last_14_days) < 7:
                # Not enough data
                return None
            
            # Split into two weeks
            week1 = last_14_days[:7]  # Days 14-8 ago
            week2 = last_14_days[7:]  # Days 7-1 ago
            
            # Calculate metrics for each week
            week1_invocations = sum(a.invocation_count for a in week1)
            week2_invocations = sum(a.invocation_count for a in week2)
            
            week1_users = sum(a.unique_users for a in week1)
            week2_users = sum(a.unique_users for a in week2)
            
            # Calculate velocity (growth rate)
            if week1_invocations > 0:
                invocation_velocity = (week2_invocations - week1_invocations) / week1_invocations
            else:
                invocation_velocity = 1.0 if week2_invocations > 0 else 0.0
            
            if week1_users > 0:
                user_velocity = (week2_users - week1_users) / week1_users
            else:
                user_velocity = 1.0 if week2_users > 0 else 0.0
            
            velocity = (invocation_velocity + user_velocity) / 2
            
            # Calculate momentum (acceleration)
            # Compare first half of week2 vs second half
            week2_first_half = week2[:len(week2)//2]
            week2_second_half = week2[len(week2)//2:]
            
            first_half_invocations = sum(a.invocation_count for a in week2_first_half)
            second_half_invocations = sum(a.invocation_count for a in week2_second_half)
            
            if first_half_invocations > 0:
                momentum = (second_half_invocations - first_half_invocations) / first_half_invocations
            else:
                momentum = 1.0 if second_half_invocations > 0 else 0.0
            
            # Calculate recency score (boost for recent activity)
            # Check if there was activity in last 3 days
            last_3_days = [a for a in last_14_days if a.date >= today - timedelta(days=3)]
            recent_activity = sum(a.invocation_count for a in last_3_days)
            recency = min(recent_activity / 100.0, 1.0)  # Normalize to 0-1
            
            # Calculate popularity score (current metrics)
            listing = MarketplaceListing.query.filter_by(agent_id=agent_id).first()
            if listing:
                # Normalize install count (log scale)
                import math
                popularity = math.log10(listing.install_count + 1) / 5.0  # Normalize to ~0-1
                popularity = min(popularity, 1.0)
            else:
                popularity = 0.0
            
            # Calculate final trending score
            trending_score = (
                velocity * 0.4 +
                momentum * 0.3 +
                recency * 0.2 +
                popularity * 0.1
            )
            
            # Normalize to 0-100 scale
            trending_score = max(0, min(100, trending_score * 100))
            
            return {
                'trending_score': Decimal(str(round(trending_score, 4))),
                'velocity': Decimal(str(round(velocity, 4))),
                'momentum': Decimal(str(round(momentum, 4)))
            }
            
        except Exception as e:
            logger.error(f"Error calculating trending score for agent {agent_id}: {str(e)}")
            return None
    
    @staticmethod
    def _update_trending_rankings():
        """Update rank field based on trending scores"""
        try:
            # Get all trending scores ordered by score
            trending_scores = AgentTrendingScore.query.order_by(
                AgentTrendingScore.trending_score.desc()
            ).all()
            
            # Update ranks
            for rank, trending in enumerate(trending_scores, start=1):
                trending.rank = rank
                trending.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            logger.info(f"Updated rankings for {len(trending_scores)} agents")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating trending rankings: {str(e)}")
            raise


# =============================================================================
# SCHEDULER INTEGRATION
# =============================================================================

def schedule_analytics_jobs():
    """
    Schedule analytics jobs to run periodically
    
    This function should be called by a task scheduler (e.g., APScheduler, Celery)
    
    Recommended schedule:
    - Daily aggregation: Run at 1:00 AM daily
    - Trending calculation: Run at 2:00 AM daily
    """
    try:
        # Run daily aggregation for yesterday
        yesterday = date.today() - timedelta(days=1)
        agg_result = AnalyticsJobService.aggregate_daily_analytics(yesterday)
        logger.info(f"Scheduled daily aggregation completed: {agg_result}")
        
        # Calculate trending scores
        trend_result = AnalyticsJobService.calculate_trending_scores()
        logger.info(f"Scheduled trending calculation completed: {trend_result}")
        
        return {
            'aggregation': agg_result,
            'trending': trend_result
        }
        
    except Exception as e:
        logger.error(f"Error in scheduled analytics jobs: {str(e)}")
        raise


if __name__ == '__main__':
    # For testing purposes
    import sys
    from src.factory import create_app
    
    app = create_app()
    with app.app_context():
        if len(sys.argv) > 1:
            if sys.argv[1] == 'aggregate':
                result = AnalyticsJobService.aggregate_daily_analytics()
                print(f"Aggregation result: {result}")
            elif sys.argv[1] == 'trending':
                result = AnalyticsJobService.calculate_trending_scores()
                print(f"Trending calculation result: {result}")
            elif sys.argv[1] == 'all':
                result = schedule_analytics_jobs()
                print(f"All jobs completed: {result}")
        else:
            print("Usage: python analytics_jobs.py [aggregate|trending|all]")

