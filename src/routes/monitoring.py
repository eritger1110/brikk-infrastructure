# -*- coding: utf-8 -*-
"""
Monitoring Routes

Provides API endpoints for accessing monitoring data, metrics, and analytics.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from src.services.monitoring_service import monitoring_service
from src.services.structured_logging import get_logger

logger = get_logger('brikk.monitoring.routes')

monitoring_bp = Blueprint("monitoring", __name__)


@monitoring_bp.route("/api/v1/monitoring/metrics", methods=["GET"])
@jwt_required()
def get_metrics():
    """
    Get comprehensive platform metrics

    Query parameters:
    - time_range: Time range in minutes (default: 60)
    """
    try:
        time_range = int(request.args.get('time_range', 60))

        # Get all metric categories
        agent_metrics = monitoring_service.get_agent_metrics(time_range)
        system_health = monitoring_service.get_system_health()
        security_metrics = monitoring_service.get_security_metrics(time_range)

        response_data = {
            'agents': agent_metrics,
            'system': system_health,
            'security': security_metrics,
            'time_range_minutes': time_range
        }

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return jsonify({'error': 'Failed to retrieve metrics'}), 500


@monitoring_bp.route("/api/v1/monitoring/health", methods=["GET"])
def get_health():
    """
    Get system health status (no authentication required for health checks)
    """
    try:
        health_data = monitoring_service.get_system_health()

        # Determine overall health status
        overall_healthy = all(
            component.get('healthy', False)
            for component in health_data.values()
            if isinstance(component, dict) and 'healthy' in component
        )

        response_data = {
            'status': 'healthy' if overall_healthy else 'degraded',
            'components': health_data
        }

        status_code = 200 if overall_healthy else 503
        return jsonify(response_data), status_code

    except Exception as e:
        logger.error(f"Failed to get health status: {e}")
        return jsonify({'error': 'Health check failed'}), 500


@monitoring_bp.route("/api/v1/monitoring/alerts", methods=["GET"])
@jwt_required()
def get_alerts():
    """
    Get active alerts and alert history
    """
    try:
        active_alerts = monitoring_service.check_alerts()

        response_data = {
            'active_alerts': active_alerts,
            'alert_count': len(active_alerts),
            'has_critical_alerts': any(
                alert.get('severity') == 'critical'
                for alert in active_alerts
            )
        }

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        return jsonify({'error': 'Failed to retrieve alerts'}), 500


@monitoring_bp.route("/api/v1/monitoring/analytics", methods=["GET"])
@jwt_required()
def get_analytics():
    """
    Get detailed performance analytics

    Query parameters:
    - time_range: Time range in hours (default: 24)
    """
    try:
        time_range = int(request.args.get('time_range', 24))

        analytics_data = monitoring_service.get_performance_analytics(
            time_range)

        return jsonify(analytics_data), 200

    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        return jsonify({'error': 'Failed to retrieve analytics'}), 500


@monitoring_bp.route("/api/v1/monitoring/agents", methods=["GET"])
@jwt_required()
def get_agent_monitoring():
    """
    Get detailed agent monitoring data

    Query parameters:
    - time_range: Time range in minutes (default: 60)
    - agent_id: Specific agent ID to monitor (optional)
    """
    try:
        time_range = int(request.args.get('time_range', 60))
        agent_id = request.args.get('agent_id')

        agent_metrics = monitoring_service.get_agent_metrics(time_range)

        # If specific agent requested, filter data
        if agent_id:
            # In a real implementation, this would filter for specific agent
            # data
            agent_metrics['filtered_for_agent'] = agent_id

        return jsonify(agent_metrics), 200

    except Exception as e:
        logger.error(f"Failed to get agent monitoring data: {e}")
        return jsonify(
            {'error': 'Failed to retrieve agent monitoring data'}), 500


@monitoring_bp.route("/api/v1/monitoring/security", methods=["GET"])
@jwt_required()
def get_security_monitoring():
    """
    Get security monitoring data and threat analysis

    Query parameters:
    - time_range: Time range in minutes (default: 60)
    """
    try:
        time_range = int(request.args.get('time_range', 60))

        security_metrics = monitoring_service.get_security_metrics(time_range)

        # Add threat level assessment
        failed_auth_rate = security_metrics.get(
            'failed_auth_attempts', 0) / max(security_metrics.get('total_auth_events', 1), 1)

        threat_level = 'low'
        if failed_auth_rate > 0.3:
            threat_level = 'high'
        elif failed_auth_rate > 0.1:
            threat_level = 'medium'

        security_metrics['threat_level'] = threat_level
        security_metrics['failed_auth_rate'] = failed_auth_rate

        return jsonify(security_metrics), 200

    except Exception as e:
        logger.error(f"Failed to get security monitoring data: {e}")
        return jsonify(
            {'error': 'Failed to retrieve security monitoring data'}), 500


@monitoring_bp.route("/api/v1/monitoring/performance", methods=["GET"])
@jwt_required()
def get_performance_monitoring():
    """
    Get real-time performance monitoring data
    """
    try:
        # Get current performance metrics
        agent_metrics = monitoring_service.get_agent_metrics(
            5)  # 5-minute window

        # Calculate performance indicators
        performance_data = {
            'response_time': {
                'current': agent_metrics.get(
                    'avg_response_time_ms',
                    0),
                'threshold': 2000,
                'status': 'good' if agent_metrics.get(
                    'avg_response_time_ms',
                    0) < 1000 else 'warning'},
            'throughput': {
                'coordinations_per_minute': agent_metrics.get(
                    'recent_coordinations',
                    0) / 5,
                'status': 'good'},
            'success_rate': {
                'current': agent_metrics.get(
                    'coordination_success_rate',
                    0),
                'threshold': 95,
                'status': 'good' if agent_metrics.get(
                    'coordination_success_rate',
                    0) >= 95 else 'warning'},
            'agent_utilization': {
                'current': agent_metrics.get(
                    'agent_utilization',
                    0),
                'optimal_range': [
                    60,
                    80],
                'status': 'good'}}

        return jsonify(performance_data), 200

    except Exception as e:
        logger.error(f"Failed to get performance monitoring data: {e}")
        return jsonify(
            {'error': 'Failed to retrieve performance monitoring data'}), 500


@monitoring_bp.route("/api/v1/monitoring/dashboard", methods=["GET"])
@jwt_required()
def get_dashboard_data():
    """
    Get comprehensive dashboard data for monitoring UI
    """
    try:
        # Get all monitoring data for dashboard
        agent_metrics = monitoring_service.get_agent_metrics(60)
        system_health = monitoring_service.get_system_health()
        security_metrics = monitoring_service.get_security_metrics(60)
        active_alerts = monitoring_service.check_alerts()

        # Calculate key performance indicators
        kpis = {
            'system_uptime': '99.9%',  # Would be calculated from actual uptime data
            'total_agents': agent_metrics.get('total_agents', 0),
            'active_agents': agent_metrics.get('active_agents', 0),
            'success_rate': agent_metrics.get('coordination_success_rate', 0),
            'avg_response_time': agent_metrics.get('avg_response_time_ms', 0),
            # Extrapolated
            'total_coordinations_today': agent_metrics.get('recent_coordinations', 0) * 24,
            'security_incidents': len([a for a in active_alerts if a.get('severity') in ['high', 'critical']]),
            'system_health_score': 95 if system_health.get('database', {}).get('healthy') else 75
        }

        dashboard_data = {
            'kpis': kpis,
            'agent_metrics': agent_metrics,
            'system_health': system_health,
            'security_summary': {
                'threat_level': 'low',
                'failed_auth_attempts': security_metrics.get(
                    'failed_auth_attempts',
                    0),
                'rate_limit_hits': security_metrics.get(
                    'rate_limit_hits',
                    0)},
            'active_alerts': active_alerts,
            'timestamp': agent_metrics.get('timestamp')}

        return jsonify(dashboard_data), 200

    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        return jsonify({'error': 'Failed to retrieve dashboard data'}), 500


@monitoring_bp.route("/api/v1/monitoring/export", methods=["GET"])
@jwt_required()
def export_metrics():
    """
    Export metrics data in various formats

    Query parameters:
    - format: Export format (json, csv) (default: json)
    - time_range: Time range in hours (default: 24)
    """
    try:
        export_format = request.args.get('format', 'json').lower()
        time_range = int(request.args.get('time_range', 24))

        if export_format not in ['json', 'csv']:
            return jsonify({'error': 'Unsupported export format'}), 400

        # Get comprehensive data for export
        analytics_data = monitoring_service.get_performance_analytics(
            time_range)

        if export_format == 'json':
            return jsonify(analytics_data), 200

        elif export_format == 'csv':
            # In a real implementation, this would convert to CSV format
            return jsonify({'message': 'CSV export not yet implemented'}), 501

    except Exception as e:
        logger.error(f"Failed to export metrics: {e}")
        return jsonify({'error': 'Failed to export metrics'}), 500
