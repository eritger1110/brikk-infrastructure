# -*- coding: utf-8 -*-
"""
Risk Scoring Middleware (Phase 7 PR-3).

Computes real-time risk assessment and applies adaptive rate limits.
"""
from flask import g, request, jsonify
from datetime import datetime, timedelta
from src.models.trust import ReputationSnapshot, RiskEvent
from src.models.api_gateway import ApiAuditLog
from src.database import get_db
from src.services.gateway_metrics import metrics
import os


# Feature flags
RISK_ENABLED = os.getenv('BRIKK_RISK_ENABLED', '1') == '1'
RISK_STEPUP_ENABLED = os.getenv('BRIKK_RISK_STEPUP_ENABLED', '0') == '1'


class RiskMiddleware:
    """Risk scoring and adaptive rate limiting middleware."""
    
    # Risk thresholds
    LOW_RISK_THRESHOLD = 70      # Reputation >= 70 = low risk
    HIGH_RISK_THRESHOLD = 40     # Reputation < 40 = high risk
    
    # Adaptive rate limit multipliers
    RISK_MULTIPLIERS = {
        'low': 1.2,      # +20% burst allowance
        'med': 1.0,      # Plan baseline
        'high': 0.5      # 50% of plan baseline
    }
    
    def __init__(self, app=None):
        """Initialize risk middleware."""
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app."""
        if not RISK_ENABLED:
            app.logger.info("Risk middleware disabled (BRIKK_RISK_ENABLED=0)")
            return
        
        app.before_request(self.assess_risk)
        app.after_request(self.add_risk_headers)
        app.logger.info("Risk middleware enabled")
    
    def assess_risk(self):
        """Assess risk level for the current request."""
        if not RISK_ENABLED:
            g.risk_level = 'med'
            g.risk_score = 50
            return
        
        # Skip risk assessment for health checks and docs
        if request.path in ['/health', '/docs', '/telemetry/health']:
            g.risk_level = 'low'
            g.risk_score = 100
            return
        
        # Get org_id from request context
        org_id = getattr(g, 'org_id', None)
        if not org_id:
            # Anonymous request - default to medium risk
            g.risk_level = 'med'
            g.risk_score = 50
            return
        
        # Compute risk score
        risk_score = self._compute_risk_score(org_id)
        risk_level = self._classify_risk(risk_score)
        
        # Store in request context
        g.risk_level = risk_level
        g.risk_score = risk_score
        
        # Log risk event if high risk
        if risk_level == 'high':
            self._log_high_risk_event(org_id)
        
        # Check for step-up verification requirement
        if RISK_STEPUP_ENABLED and risk_level == 'high' and request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            verification = request.headers.get('X-Brikk-Verification')
            if not verification or verification != 'otp':
                return jsonify({
                    'error': 'step_up_required',
                    'message': 'High-risk write operation requires step-up verification',
                    'required_header': 'X-Brikk-Verification: otp',
                    'risk_level': risk_level,
                    'request_id': getattr(g, 'request_id', None)
                }), 403
        
        # Update metrics
        if hasattr(metrics, 'risk_requests_total'):
            metrics.risk_requests_total.labels(risk=risk_level).inc()
    
    def _compute_risk_score(self, org_id: str) -> int:
        """
        Compute risk score (0-100, higher = less risky) based on:
        - Reputation score
        - Recent risk events
        - Auth anomalies
        - Abuse heuristics
        """
        db = next(get_db())
        
        # Factor 1: Reputation (60% weight)
        reputation_score = self._get_reputation_score(db, org_id)
        reputation_component = reputation_score * 0.6
        
        # Factor 2: Recent risk events (25% weight)
        risk_events_score = self._compute_risk_events_score(db, org_id)
        risk_events_component = risk_events_score * 0.25
        
        # Factor 3: Auth anomalies (15% weight)
        auth_score = self._compute_auth_score(db, org_id)
        auth_component = auth_score * 0.15
        
        # Combined risk score
        total_score = reputation_component + risk_events_component + auth_component
        
        return int(round(max(0, min(100, total_score))))
    
    def _get_reputation_score(self, db, org_id: str) -> int:
        """Get reputation score from cache or default."""
        snapshot = ReputationSnapshot.get_latest(db, 'org', org_id, '30d')
        if snapshot:
            return snapshot.score
        return 50  # Neutral default
    
    def _compute_risk_events_score(self, db, org_id: str) -> int:
        """Compute score based on recent risk events."""
        # Get risk events from last 7 days
        cutoff = datetime.utcnow() - timedelta(days=7)
        events = db.query(RiskEvent).filter(
            RiskEvent.org_id == org_id,
            RiskEvent.created_at >= cutoff
        ).all()
        
        if not events:
            return 100  # No events = good
        
        # Count by severity
        high_count = sum(1 for e in events if e.severity == 'high')
        med_count = sum(1 for e in events if e.severity == 'med')
        low_count = sum(1 for e in events if e.severity == 'low')
        
        # Weighted penalty
        penalty = (high_count * 20) + (med_count * 10) + (low_count * 5)
        score = 100 - min(100, penalty)
        
        return max(0, score)
    
    def _compute_auth_score(self, db, org_id: str) -> int:
        """Compute score based on auth patterns."""
        # Get recent auth failures
        cutoff = datetime.utcnow() - timedelta(days=7)
        auth_fails = db.query(RiskEvent).filter(
            RiskEvent.org_id == org_id,
            RiskEvent.type == 'auth_fail',
            RiskEvent.created_at >= cutoff
        ).count()
        
        # Penalty for auth failures
        penalty = min(100, auth_fails * 10)
        score = 100 - penalty
        
        return max(0, score)
    
    def _classify_risk(self, risk_score: int) -> str:
        """Classify risk level based on score."""
        if risk_score >= self.LOW_RISK_THRESHOLD:
            return 'low'
        elif risk_score >= self.HIGH_RISK_THRESHOLD:
            return 'med'
        else:
            return 'high'
    
    def _log_high_risk_event(self, org_id: str):
        """Log a high-risk event."""
        try:
            db = next(get_db())
            RiskEvent.log_event(
                db,
                org_id=org_id,
                event_type='high_risk_request',
                severity='high',
                actor_id=getattr(g, 'actor_id', None),
                meta={
                    'path': request.path,
                    'method': request.method,
                    'ip': request.remote_addr,
                    'risk_score': g.risk_score
                }
            )
        except Exception as e:
            # Don't fail request if logging fails
            if self.app:
                self.app.logger.error(f"Failed to log high-risk event: {e}")
    
    def add_risk_headers(self, response):
        """Add risk-related headers to response."""
        if not RISK_ENABLED:
            return response
        
        risk_level = getattr(g, 'risk_level', 'med')
        risk_score = getattr(g, 'risk_score', 50)
        
        response.headers['X-Risk-Level'] = risk_level
        response.headers['X-Risk-Score-Bucket'] = self._bucket_score(risk_score)
        
        # Add adaptive limit info if rate limiting is active
        if hasattr(g, 'rate_limit_tier'):
            multiplier = self.RISK_MULTIPLIERS.get(risk_level, 1.0)
            response.headers['X-Adaptive-Limit-Multiplier'] = f"{multiplier}x"
        
        return response
    
    def _bucket_score(self, score: int) -> str:
        """Bucket risk score for privacy."""
        bucket_start = (score // 20) * 20
        bucket_end = bucket_start + 20
        return f"{bucket_start}-{bucket_end}"
    
    def get_adaptive_limit_multiplier(self, risk_level: str = None) -> float:
        """Get rate limit multiplier for risk level."""
        if not RISK_ENABLED:
            return 1.0
        
        if risk_level is None:
            risk_level = getattr(g, 'risk_level', 'med')
        
        multiplier = self.RISK_MULTIPLIERS.get(risk_level, 1.0)
        
        # Update metrics
        if hasattr(metrics, 'adaptive_limit_applied'):
            metrics.adaptive_limit_applied.labels(risk=risk_level).inc()
        
        return multiplier


# Global instance
risk_middleware = RiskMiddleware()

