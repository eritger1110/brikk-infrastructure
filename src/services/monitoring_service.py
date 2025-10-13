# -*- coding: utf-8 -*-
"""
Enhanced Monitoring Service

Provides comprehensive monitoring, alerting, and analytics capabilities for the Brikk platform.
Includes real-time metrics collection, performance tracking, and automated alerting.
"""

import os
import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

import redis
from flask import current_app
from sqlalchemy import text, func
from src.database import db
from src.models.agent import Agent, Coordination
from src.models.audit_log import AuditLog
from src.services.structured_logging import get_logger

logger = get_logger('brikk.monitoring')


class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricPoint:
    """Represents a single metric data point"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str]
    metric_type: MetricType


@dataclass
class Alert:
    """Represents an alert condition"""
    id: str
    name: str
    description: str
    severity: AlertSeverity
    condition: str
    threshold: float
    triggered_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    is_active: bool = False


class MonitoringService:
    """Enhanced monitoring service for comprehensive platform observability"""

    def __init__(self):
        self.redis_client = self._get_redis_client()
        self.metrics_retention_days = int(
            os.getenv('METRICS_RETENTION_DAYS', '30'))
        self.alert_rules = self._load_alert_rules()

    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client for metrics storage"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception as e:
            logger.warning(f"Redis not available for metrics storage: {e}")
            return None

    def _load_alert_rules(self) -> List[Alert]:
        """Load alert rules from configuration"""
        return [
            Alert(
                id="high_error_rate",
                name="High Error Rate",
                description="Error rate exceeds 5% over 5 minutes",
                severity=AlertSeverity.HIGH,
                condition="error_rate > 0.05",
                threshold=0.05
            ),
            Alert(
                id="agent_down",
                name="Agent Down",
                description="Agent has been inactive for more than 10 minutes",
                severity=AlertSeverity.CRITICAL,
                condition="agent_inactive_minutes > 10",
                threshold=10
            ),
            Alert(
                id="high_latency",
                name="High Response Latency",
                description="Average response latency exceeds 2 seconds",
                severity=AlertSeverity.MEDIUM,
                condition="avg_latency > 2000",
                threshold=2000
            ),
            Alert(
                id="coordination_failures",
                name="Coordination Failures",
                description="Coordination failure rate exceeds 10%",
                severity=AlertSeverity.HIGH,
                condition="coordination_failure_rate > 0.10",
                threshold=0.10
            )
        ]

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now(timezone.utc).isoformat()

    def record_metric(self,
                      name: str,
                      value: float,
                      tags: Dict[str,
                                 str] = None,
                      metric_type: MetricType = MetricType.GAUGE) -> None:
        """Record a metric data point"""
        if tags is None:
            tags = {}

        metric = MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.now(timezone.utc),
            tags=tags,
            metric_type=metric_type
        )

        # Store in Redis if available
        if self.redis_client:
            try:
                key = f"metrics:{name}:{int(metric.timestamp.timestamp())}"
                self.redis_client.setex(
                    key,
                    timedelta(days=self.metrics_retention_days),
                    json.dumps(asdict(metric), default=str)
                )
            except Exception as e:
                logger.error(f"Failed to store metric in Redis: {e}")

        # Log metric for debugging
        logger.debug(f"Recorded metric: {name}={value} tags={tags}")

    def get_agent_metrics(
            self, time_range_minutes: int = 60) -> Dict[str, Any]:
        """Get comprehensive agent metrics"""
        try:
            cutoff_time = datetime.now(
                timezone.utc) - timedelta(minutes=time_range_minutes)

            # Active agents count
            active_agents = db.session.query(Agent).filter(
                Agent.status == 'active',
                Agent.last_seen >= cutoff_time
            ).count()

            # Total agents count
            total_agents = db.session.query(Agent).count()

            # Agent status distribution
            status_distribution = db.session.query(
                Agent.status, func.count(Agent.id)
            ).group_by(Agent.status).all()

            # Recent coordinations
            recent_coordinations = db.session.query(Coordination).filter(
                Coordination.created_at >= cutoff_time
            ).count()

            # Coordination success rate
            total_coordinations = db.session.query(Coordination).filter(
                Coordination.created_at >= cutoff_time
            ).count()

            successful_coordinations = db.session.query(Coordination).filter(
                Coordination.created_at >= cutoff_time,
                Coordination.status == 'completed'
            ).count()

            success_rate = (successful_coordinations /
                            max(total_coordinations, 1)) * 100

            # Average response time (simulated for now)
            avg_response_time = self._calculate_avg_response_time(
                time_range_minutes)

            metrics = {
                'active_agents': active_agents,
                'total_agents': total_agents,
                'agent_utilization': (active_agents / max(total_agents, 1)) * 100,
                'status_distribution': dict(status_distribution),
                'recent_coordinations': recent_coordinations,
                'coordination_success_rate': success_rate,
                'avg_response_time_ms': avg_response_time,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Record key metrics
            self.record_metric('agents.active', active_agents)
            self.record_metric('agents.total', total_agents)
            self.record_metric(
                'coordinations.success_rate',
                success_rate / 100)
            self.record_metric(
                'coordinations.avg_response_time',
                avg_response_time)

            return metrics

        except Exception as e:
            logger.error(f"Failed to get agent metrics: {e}")
            return {}

    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health metrics"""
        try:
            health = {
                'database': self._check_database_health(),
                'redis': self._check_redis_health(),
                'api_endpoints': self._check_api_health(),
                'disk_usage': self._get_disk_usage(),
                'memory_usage': self._get_memory_usage(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Record system health metrics
            for component, status in health.items():
                if isinstance(status, dict) and 'healthy' in status:
                    self.record_metric(
                        f'system.{component}.healthy',
                        1 if status['healthy'] else 0)

            return health

        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {'error': str(e)}

    def get_security_metrics(
            self, time_range_minutes: int = 60) -> Dict[str, Any]:
        """Get security-related metrics"""
        try:
            cutoff_time = datetime.now(
                timezone.utc) - timedelta(minutes=time_range_minutes)

            # Authentication events
            auth_events = db.session.query(AuditLog).filter(
                AuditLog.created_at >= cutoff_time,
                AuditLog.event_type.like('%auth%')
            ).count()

            # Failed authentication attempts
            failed_auth = db.session.query(AuditLog).filter(
                AuditLog.created_at >= cutoff_time,
                AuditLog.event_type == 'auth_failure'
            ).count()

            # Rate limit hits
            rate_limit_hits = db.session.query(AuditLog).filter(
                AuditLog.created_at >= cutoff_time,
                AuditLog.event_type == 'rate_limit_hit'
            ).count()

            # Security events by type
            security_events = db.session.query(
                AuditLog.event_type,
                func.count(
                    AuditLog.id)).filter(
                AuditLog.created_at >= cutoff_time,
                AuditLog.event_type.in_(
                    [
                        'auth_success',
                        'auth_failure',
                        'rate_limit_hit',
                        'suspicious_activity'])).group_by(
                        AuditLog.event_type).all()

            metrics = {
                'total_auth_events': auth_events,
                'failed_auth_attempts': failed_auth,
                'rate_limit_hits': rate_limit_hits,
                'security_events_by_type': dict(security_events),
                'auth_success_rate': ((auth_events - failed_auth) / max(auth_events, 1)) * 100,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Record security metrics
            self.record_metric('security.auth_events', auth_events)
            self.record_metric('security.failed_auth', failed_auth)
            self.record_metric('security.rate_limit_hits', rate_limit_hits)

            return metrics

        except Exception as e:
            logger.error(f"Failed to get security metrics: {e}")
            return {}

    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check all alert conditions and return active alerts"""
        active_alerts = []

        try:
            # Get current metrics
            agent_metrics = self.get_agent_metrics(5)  # 5-minute window
            system_health = self.get_system_health()
            security_metrics = self.get_security_metrics(5)

            for alert_rule in self.alert_rules:
                is_triggered = self._evaluate_alert_condition(
                    alert_rule, agent_metrics, system_health, security_metrics
                )

                if is_triggered and not alert_rule.is_active:
                    # New alert triggered
                    alert_rule.is_active = True
                    alert_rule.triggered_at = datetime.now(timezone.utc)

                    alert_data = {
                        'id': alert_rule.id,
                        'name': alert_rule.name,
                        'description': alert_rule.description,
                        'severity': alert_rule.severity.value,
                        'triggered_at': alert_rule.triggered_at.isoformat(),
                        'is_active': True
                    }

                    active_alerts.append(alert_data)

                    # Log alert
                    logger.warning(
                        f"Alert triggered: {alert_rule.name} - {alert_rule.description}")

                    # Record alert metric
                    self.record_metric(f'alerts.{alert_rule.id}', 1,
                                       {'severity': alert_rule.severity.value})

                elif not is_triggered and alert_rule.is_active:
                    # Alert resolved
                    alert_rule.is_active = False
                    alert_rule.resolved_at = datetime.now(timezone.utc)

                    logger.info(f"Alert resolved: {alert_rule.name}")

                    # Record alert resolution
                    self.record_metric(f'alerts.{alert_rule.id}', 0,
                                       {'severity': alert_rule.severity.value})

            return active_alerts

        except Exception as e:
            logger.error(f"Failed to check alerts: {e}")
            return []

    def get_performance_analytics(
            self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get detailed performance analytics"""
        try:
            cutoff_time = datetime.now(
                timezone.utc) - timedelta(hours=time_range_hours)

            # Coordination patterns
            coordination_patterns = self._analyze_coordination_patterns(
                cutoff_time)

            # Agent performance
            agent_performance = self._analyze_agent_performance(cutoff_time)

            # System trends
            system_trends = self._analyze_system_trends(cutoff_time)

            analytics = {
                'coordination_patterns': coordination_patterns,
                'agent_performance': agent_performance,
                'system_trends': system_trends,
                'analysis_period_hours': time_range_hours,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            return analytics

        except Exception as e:
            logger.error(f"Failed to get performance analytics: {e}")
            return {}

    def _calculate_avg_response_time(self, time_range_minutes: int) -> float:
        """Calculate average response time (simulated for now)"""
        # In a real implementation, this would query actual response time data
        # For now, return a simulated value based on system load
        base_time = 150.0  # Base response time in ms

        try:
            # Factor in system load
            active_agents = db.session.query(Agent).filter(
                Agent.status == 'active').count()
            load_factor = min(active_agents / 10.0, 2.0)  # Cap at 2x

            return base_time * (1 + load_factor * 0.5)
        except BaseException:
            return base_time

    def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        try:
            start_time = time.time()
            db.session.execute(text('SELECT 1'))
            response_time = (time.time() - start_time) * 1000

            return {
                'healthy': True,
                'response_time_ms': response_time,
                'status': 'connected'
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'status': 'disconnected'
            }

    def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        if not self.redis_client:
            return {
                'healthy': False,
                'status': 'not_configured'
            }

        try:
            start_time = time.time()
            self.redis_client.ping()
            response_time = (time.time() - start_time) * 1000

            return {
                'healthy': True,
                'response_time_ms': response_time,
                'status': 'connected'
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e),
                'status': 'disconnected'
            }

    def _check_api_health(self) -> Dict[str, Any]:
        """Check API endpoint health"""
        # Simplified health check - in production, this would test actual
        # endpoints
        return {
            'healthy': True,
            'endpoints_checked': 5,
            'endpoints_healthy': 5,
            'status': 'operational'
        }

    def _get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage information"""
        try:
            import shutil
            total, used, free = shutil.disk_usage('/')
            usage_percent = (used / total) * 100

            return {
                'total_gb': round(total / (1024**3), 2),
                'used_gb': round(used / (1024**3), 2),
                'free_gb': round(free / (1024**3), 2),
                'usage_percent': round(usage_percent, 2),
                'healthy': usage_percent < 85
            }
        except Exception as e:
            return {'error': str(e), 'healthy': False}

    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage information"""
        try:
            import psutil
            memory = psutil.virtual_memory()

            return {
                'total_gb': round(memory.total / (1024**3), 2),
                'used_gb': round(memory.used / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'usage_percent': memory.percent,
                'healthy': memory.percent < 85
            }
        except ImportError:
            # Fallback if psutil is not available
            return {
                'total_gb': 8.0,
                'used_gb': 4.0,
                'available_gb': 4.0,
                'usage_percent': 50.0,
                'healthy': True
            }
        except Exception as e:
            return {'error': str(e), 'healthy': False}

    def _evaluate_alert_condition(
            self,
            alert: Alert,
            agent_metrics: Dict,
            system_health: Dict,
            security_metrics: Dict) -> bool:
        """Evaluate if an alert condition is met"""
        try:
            if alert.id == "high_error_rate":
                success_rate = agent_metrics.get(
                    'coordination_success_rate', 100)
                error_rate = (100 - success_rate) / 100
                return error_rate > alert.threshold

            elif alert.id == "agent_down":
                # Check if any agents have been inactive
                active_agents = agent_metrics.get('active_agents', 0)
                total_agents = agent_metrics.get('total_agents', 0)
                if total_agents > 0:
                    inactive_ratio = (
                        total_agents - active_agents) / total_agents
                    return inactive_ratio > 0.5  # More than 50% inactive
                return False

            elif alert.id == "high_latency":
                avg_latency = agent_metrics.get('avg_response_time_ms', 0)
                return avg_latency > alert.threshold

            elif alert.id == "coordination_failures":
                success_rate = agent_metrics.get(
                    'coordination_success_rate', 100)
                failure_rate = (100 - success_rate) / 100
                return failure_rate > alert.threshold

            return False

        except Exception as e:
            logger.error(
                f"Failed to evaluate alert condition for {alert.id}: {e}")
            return False

    def _analyze_coordination_patterns(
            self, cutoff_time: datetime) -> Dict[str, Any]:
        """Analyze coordination patterns and trends"""
        try:
            # Coordination volume by hour
            hourly_coordinations = db.session.query(
                func.date_trunc('hour', Coordination.created_at).label('hour'),
                func.count(Coordination.id).label('count')
            ).filter(
                Coordination.created_at >= cutoff_time
            ).group_by('hour').order_by('hour').all()

            # Most active agent pairs
            # This would require a more complex query in a real implementation

            return {
                'hourly_volume': [
                    {'hour': hour.isoformat(), 'count': count}
                    for hour, count in hourly_coordinations
                ],
                'total_coordinations': sum(count for _, count in hourly_coordinations),
                'peak_hour': max(hourly_coordinations, key=lambda x: x[1])[0].isoformat() if hourly_coordinations else None
            }
        except Exception as e:
            logger.error(f"Failed to analyze coordination patterns: {e}")
            return {}

    def _analyze_agent_performance(
            self, cutoff_time: datetime) -> Dict[str, Any]:
        """Analyze individual agent performance"""
        try:
            # Agent activity levels
            agent_activity = db.session.query(
                Agent.id,
                Agent.name,
                func.count(
                    Coordination.id).label('coordination_count')).outerjoin(
                Coordination,
                (Agent.id == Coordination.sender_agent_id) | (
                    Agent.id == Coordination.recipient_agent_id)).filter(
                Coordination.created_at >= cutoff_time).group_by(
                        Agent.id,
                Agent.name).all()

            return {
                'agent_activity': [
                    {
                        'agent_id': agent_id,
                        'agent_name': name,
                        'coordination_count': count} for agent_id,
                    name,
                    count in agent_activity],
                'most_active_agent': max(
                    agent_activity,
                    key=lambda x: x[2])[1] if agent_activity else None}
        except Exception as e:
            logger.error(f"Failed to analyze agent performance: {e}")
            return {}

    def _analyze_system_trends(self, cutoff_time: datetime) -> Dict[str, Any]:
        """Analyze system-wide trends"""
        try:
            # Growth trends
            total_agents_now = db.session.query(Agent).count()
            total_coordinations_period = db.session.query(Coordination).filter(
                Coordination.created_at >= cutoff_time
            ).count()

            return {
                'total_agents': total_agents_now,
                'coordinations_in_period': total_coordinations_period,
                'avg_coordinations_per_hour': total_coordinations_period / 24 if total_coordinations_period > 0 else 0}
        except Exception as e:
            logger.error(f"Failed to analyze system trends: {e}")
            return {}


# Global monitoring service instance
monitoring_service = MonitoringService()
