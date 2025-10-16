# -*- coding: utf-8 -*-
"""
Reputation Engine (Phase 7 PR-2).

Computes 0-100 reputation scores for orgs and agents based on multiple signals.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from sqlalchemy import func
from src.models.trust import ReputationSnapshot, Attestation, RiskEvent
from src.models.usage_ledger import UsageLedger
from src.models.api_gateway import ApiAuditLog
import os


# Configurable decay horizon (days)
REPUTATION_DECAY_DAYS = int(os.getenv('BRIKK_REPUTATION_DECAY_DAYS', '90'))


class ReputationEngine:
    """Reputation scoring engine for orgs and agents."""
    
    # Scoring weights (must sum to 1.0)
    WEIGHTS = {
        'reliability': 0.30,      # 5xx rate, timeouts, p95 latency
        'commerce': 0.20,         # Transaction volume, refunds, chargebacks
        'hygiene': 0.15,          # Auth failures, key rotation, rate limits
        'attestations': 0.20,     # Web-of-trust vouches
        'usage': 0.15            # Usage steadiness and growth
    }
    
    def __init__(self, db):
        """Initialize reputation engine with database session."""
        self.db = db
    
    def compute_score(self, subject_type: str, subject_id: str, window: str = '30d') -> Tuple[int, Dict]:
        """
        Compute reputation score (0-100) for a subject.
        
        Returns: (score, reason_dict)
        """
        # Parse window to days
        window_days = self._parse_window(window)
        cutoff = datetime.utcnow() - timedelta(days=window_days)
        
        # Compute individual factor scores
        reliability_score = self._compute_reliability(subject_type, subject_id, cutoff)
        commerce_score = self._compute_commerce(subject_type, subject_id, cutoff)
        hygiene_score = self._compute_hygiene(subject_type, subject_id, cutoff)
        attestations_score = self._compute_attestations(subject_type, subject_id, cutoff)
        usage_score = self._compute_usage(subject_type, subject_id, cutoff)
        
        # Weighted sum
        total_score = (
            reliability_score * self.WEIGHTS['reliability'] +
            commerce_score * self.WEIGHTS['commerce'] +
            hygiene_score * self.WEIGHTS['hygiene'] +
            attestations_score * self.WEIGHTS['attestations'] +
            usage_score * self.WEIGHTS['usage']
        )
        
        # Round to integer, clamp to 0-100
        final_score = max(0, min(100, int(round(total_score))))
        
        # Build reason dict with top factors
        reason = {
            'factors': {
                'reliability': {
                    'score': reliability_score,
                    'weight': self.WEIGHTS['reliability'],
                    'contribution': reliability_score * self.WEIGHTS['reliability']
                },
                'commerce': {
                    'score': commerce_score,
                    'weight': self.WEIGHTS['commerce'],
                    'contribution': commerce_score * self.WEIGHTS['commerce']
                },
                'hygiene': {
                    'score': hygiene_score,
                    'weight': self.WEIGHTS['hygiene'],
                    'contribution': hygiene_score * self.WEIGHTS['hygiene']
                },
                'attestations': {
                    'score': attestations_score,
                    'weight': self.WEIGHTS['attestations'],
                    'contribution': attestations_score * self.WEIGHTS['attestations']
                },
                'usage': {
                    'score': usage_score,
                    'weight': self.WEIGHTS['usage'],
                    'contribution': usage_score * self.WEIGHTS['usage']
                }
            },
            'window': window,
            'window_days': window_days,
            'computed_at': datetime.utcnow().isoformat()
        }
        
        return final_score, reason
    
    def _parse_window(self, window: str) -> int:
        """Parse window string to days."""
        if window == '7d':
            return 7
        elif window == '30d':
            return 30
        elif window == '90d':
            return 90
        else:
            return 30  # Default
    
    def _compute_reliability(self, subject_type: str, subject_id: str, cutoff: datetime) -> float:
        """
        Compute reliability score (0-100) based on:
        - 5xx error rate
        - Timeout rate
        - P95 latency vs SLO
        """
        # Query audit logs for error rates
        if subject_type == 'org':
            logs = self.db.query(ApiAuditLog).filter(
                ApiAuditLog.org_id == subject_id,
                ApiAuditLog.created_at >= cutoff
            ).all()
        else:
            # For agents, we'd need to track agent_id in audit logs
            # For now, return baseline score
            return 75.0
        
        if not logs:
            return 75.0  # Neutral score for no data
        
        total_requests = len(logs)
        error_5xx = sum(1 for log in logs if log.status >= 500)
        error_rate = error_5xx / total_requests if total_requests > 0 else 0
        
        # Score: 100 - (error_rate * 100 * penalty_multiplier)
        # Error rate of 0% = 100, 1% = 95, 5% = 75, 10% = 50
        reliability_score = 100 - (error_rate * 100 * 5)
        
        return max(0, min(100, reliability_score))
    
    def _compute_commerce(self, subject_type: str, subject_id: str, cutoff: datetime) -> float:
        """
        Compute commerce score (0-100) based on:
        - Transaction volume (positive signal)
        - Refund/chargeback ratio (negative signal)
        - Dispute counts (negative signal)
        """
        # Query usage ledger for transaction volume
        if subject_type == 'org':
            usage_count = self.db.query(func.count(UsageLedger.id)).filter(
                UsageLedger.org_id == int(subject_id) if subject_id.isdigit() else None,
                UsageLedger.timestamp >= cutoff
            ).scalar() or 0
        else:
            usage_count = 0
        
        # Query risk events for chargebacks/disputes
        if subject_type == 'org':
            risk_events = self.db.query(RiskEvent).filter(
                RiskEvent.org_id == subject_id,
                RiskEvent.type.in_(['chargeback', 'refund', 'dispute']),
                RiskEvent.created_at >= cutoff
            ).count()
        else:
            risk_events = 0
        
        # Score based on volume (logarithmic) and risk events
        volume_score = min(50, (usage_count / 100) * 50) if usage_count > 0 else 25
        risk_penalty = min(50, risk_events * 10)
        
        commerce_score = volume_score + (50 - risk_penalty)
        
        return max(0, min(100, commerce_score))
    
    def _compute_hygiene(self, subject_type: str, subject_id: str, cutoff: datetime) -> float:
        """
        Compute hygiene score (0-100) based on:
        - Failed auth attempts
        - Key rotation cadence
        - Rate limit hits
        """
        # Query risk events for auth failures and rate limits
        if subject_type == 'org':
            auth_fails = self.db.query(RiskEvent).filter(
                RiskEvent.org_id == subject_id,
                RiskEvent.type == 'auth_fail',
                RiskEvent.created_at >= cutoff
            ).count()
            
            rate_limit_hits = self.db.query(RiskEvent).filter(
                RiskEvent.org_id == subject_id,
                RiskEvent.type == 'rate_limit_spike',
                RiskEvent.created_at >= cutoff
            ).count()
        else:
            auth_fails = 0
            rate_limit_hits = 0
        
        # Start at 100, deduct for issues
        hygiene_score = 100.0
        hygiene_score -= min(30, auth_fails * 5)  # Max -30 for auth failures
        hygiene_score -= min(20, rate_limit_hits * 10)  # Max -20 for rate limits
        
        return max(0, min(100, hygiene_score))
    
    def _compute_attestations(self, subject_type: str, subject_id: str, cutoff: datetime) -> float:
        """
        Compute attestations score (0-100) based on:
        - Number of attestations
        - Weight of attestations
        - Time decay (90d)
        """
        attestations = self.db.query(Attestation).filter(
            Attestation.subject_type == subject_type,
            Attestation.subject_id == subject_id,
            Attestation.created_at >= cutoff
        ).all()
        
        if not attestations:
            return 50.0  # Neutral score for no attestations
        
        # Compute weighted score with time decay
        total_weight = 0.0
        for att in attestations:
            age_days = (datetime.utcnow() - att.created_at).days
            decay_factor = max(0, 1 - (age_days / REPUTATION_DECAY_DAYS))
            total_weight += att.weight * decay_factor
        
        # Cap at 10 effective attestations (weight * decay)
        capped_weight = min(10, total_weight)
        
        # Score: 50 + (capped_weight * 5)
        # 0 attestations = 50, 10 attestations = 100
        attestations_score = 50 + (capped_weight * 5)
        
        return max(0, min(100, attestations_score))
    
    def _compute_usage(self, subject_type: str, subject_id: str, cutoff: datetime) -> float:
        """
        Compute usage score (0-100) based on:
        - Usage steadiness (variance)
        - Usage growth trend
        """
        # Query usage ledger for steadiness
        if subject_type == 'org':
            usage_records = self.db.query(UsageLedger).filter(
                UsageLedger.org_id == int(subject_id) if subject_id.isdigit() else None,
                UsageLedger.timestamp >= cutoff
            ).count()
        else:
            usage_records = 0
        
        if usage_records == 0:
            return 50.0  # Neutral for no usage
        
        # Simple heuristic: more usage = higher score (up to a point)
        # Steadiness would require more complex time-series analysis
        usage_score = min(100, 50 + (usage_records / 10))
        
        return max(0, min(100, usage_score))
    
    def recompute_all(self, window: str = '30d', subject_type: str = None, subject_id: str = None):
        """
        Batch recompute reputation for all subjects or a specific subject.
        
        Args:
            window: Time window ('7d', '30d', '90d')
            subject_type: Optional filter by subject type
            subject_id: Optional filter by subject ID
        """
        # If specific subject provided, compute only that one
        if subject_type and subject_id:
            score, reason = self.compute_score(subject_type, subject_id, window)
            ReputationSnapshot.create_snapshot(
                self.db, subject_type, subject_id, score, window, reason
            )
            return [(subject_type, subject_id, score)]
        
        # Otherwise, compute for all known subjects
        # For now, we'll need to query organizations and agents tables
        # This is a simplified version - production would need more sophisticated discovery
        results = []
        
        # Compute for all orgs (stub - would need to query organizations table)
        # For demo purposes, just return empty list
        
        return results
    
    def get_top_factors(self, reason: Dict, limit: int = 3) -> List[Dict]:
        """Extract top N contributing factors from reason dict."""
        factors = reason.get('factors', {})
        sorted_factors = sorted(
            factors.items(),
            key=lambda x: x[1]['contribution'],
            reverse=True
        )
        
        return [
            {
                'factor': name,
                'score': data['score'],
                'weight': data['weight'],
                'contribution': data['contribution']
            }
            for name, data in sorted_factors[:limit]
        ]
    
    def bucket_score(self, score: int) -> str:
        """Bucket score for privacy (e.g., 85 -> '80-90')."""
        bucket_start = (score // 10) * 10
        bucket_end = bucket_start + 10
        return f"{bucket_start}-{bucket_end}"

