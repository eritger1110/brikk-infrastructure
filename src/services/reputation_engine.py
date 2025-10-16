"""
Reputation scoring engine for Phase 7 trust layer.
"""

from datetime import datetime, timedelta
from src.models.trust import ReputationSnapshot, Attestation, RiskEvent
from src.models.usage_ledger import UsageLedger
from src.database import db


class ReputationEngine:
    """Computes and updates reputation scores for orgs and agents."""

    @staticmethod
    def bucket_score(score: int) -> str:
        """Convert raw score to privacy-preserving bucket."""
        if score is None:
            return None
        if score >= 80:
            return "80-100"
        elif score >= 60:
            return "60-80"
        elif score >= 40:
            return "40-60"
        elif score >= 20:
            return "20-40"
        else:
            return "0-20"

    @staticmethod
    def compute_reputation(subject_type: str, subject_id: str, window_days: int = 30) -> dict:
        """
        Compute reputation score for an org or agent.
        
        Returns dict with:
        - score: 0-100 overall score
        - components: breakdown by category
        """
        cutoff = datetime.utcnow() - timedelta(days=window_days)
        
        # Component scores (each 0-100)
        reliability_score = ReputationEngine._compute_reliability(subject_type, subject_id, cutoff)
        commerce_score = ReputationEngine._compute_commerce(subject_type, subject_id, cutoff)
        hygiene_score = ReputationEngine._compute_hygiene(subject_type, subject_id, cutoff)
        
        # Weighted average
        overall_score = int(
            reliability_score * 0.4 +
            commerce_score * 0.3 +
            hygiene_score * 0.3
        )
        
        return {
            "score": max(0, min(100, overall_score)),
            "components": {
                "reliability": reliability_score,
                "commerce": commerce_score,
                "hygiene": hygiene_score
            }
        }

    @staticmethod
    def _compute_reliability(subject_type: str, subject_id: str, cutoff: datetime) -> int:
        """Compute reliability score based on uptime, SLO, response times."""
        # Simplified: Start at 80, deduct for risk events
        base_score = 80
        
        if subject_type == 'org':
            # Check risk events
            risk_events = RiskEvent.query.filter(
                RiskEvent.org_id == int(subject_id) if subject_id.isdigit() else 0,
                RiskEvent.created_at >= cutoff
            ).all()
            
            # Deduct points for risk events
            for event in risk_events:
                if event.severity == 'high':
                    base_score -= 10
                elif event.severity == 'medium':
                    base_score -= 5
                else:
                    base_score -= 2
        
        return max(0, min(100, base_score))

    @staticmethod
    def _compute_commerce(subject_type: str, subject_id: str, cutoff: datetime) -> int:
        """Compute commerce score based on transaction volume, payment history."""
        # Simplified: Start at 70, boost for usage
        base_score = 70
        
        if subject_type == 'org':
            # Check usage ledger for activity
            usage_count = UsageLedger.query.filter(
                UsageLedger.org_id == int(subject_id) if subject_id.isdigit() else 0,
                UsageLedger.timestamp >= cutoff
            ).count()
            
            # Boost score based on activity
            if usage_count > 1000:
                base_score += 20
            elif usage_count > 100:
                base_score += 10
            elif usage_count > 10:
                base_score += 5
        
        return max(0, min(100, base_score))

    @staticmethod
    def _compute_hygiene(subject_type: str, subject_id: str, cutoff: datetime) -> int:
        """Compute hygiene score based on attestations, compliance."""
        # Simplified: Start at 75, boost for attestations
        base_score = 75
        
        # Check attestations
        attestations = Attestation.get_active_for_subject(subject_type, subject_id)
        
        # Boost score based on attestations with time decay
        for att in attestations:
            age_days = (datetime.utcnow() - att.created_at).days
            decay_factor = max(0.5, 1.0 - (age_days / 365))  # Decay over 1 year
            boost = (att.score / 100) * 10 * decay_factor
            base_score += boost
        
        return max(0, min(100, int(base_score)))

    @staticmethod
    def update_snapshot(subject_type: str, subject_id: str, window_days: int = 30):
        """Compute and save a new reputation snapshot."""
        result = ReputationEngine.compute_reputation(subject_type, subject_id, window_days)
        
        snapshot = ReputationSnapshot(
            subject_type=subject_type,
            subject_id=subject_id,
            score=result['score'],
            window_days=window_days,
            components=result['components']
        )
        
        db.session.add(snapshot)
        db.session.commit()
        
        return snapshot

