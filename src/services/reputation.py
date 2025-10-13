# -*- coding: utf-8 -*-
"""
Reputation Service

Handles the calculation and updating of agent and organization reputation scores.
"""

from src.database import db
from src.models.economy import ReputationScore


class ReputationService:

    def update_reputation(self, org_id: str, agent_id: str, signal_dict: dict):
        """Updates the reputation score for a given agent or organization."""
        # This is a placeholder for the actual reputation calculation logic.
        # In a real implementation, this would involve a more sophisticated
        # scoring model based on the provided signals.
        score = self._calculate_score(signal_dict)

        reputation = ReputationScore.query.filter_by(
            org_id=org_id, agent_id=agent_id).first()
        if not reputation:
            reputation = ReputationScore(org_id=org_id, agent_id=agent_id)
            db.session.add(reputation)

        reputation.score = score
        reputation.signals = signal_dict
        db.session.commit()

    def _calculate_score(self, signals: dict) -> float:
        """Calculates a reputation score based on a dictionary of signals."""
        # Simple scoring model for demonstration purposes
        success_rate = signals.get("success_rate", 0)
        volume = signals.get("volume", 0)
        latency = signals.get("latency", 1000)

        score = (success_rate * 50) + (volume / 100) - (latency / 100)
        return max(0, min(100, score))
