"""
Reputation Routes

Provides API endpoints for accessing reputation scores and summaries.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.economy import ReputationScore

reputation_bp = Blueprint("reputation_bp", __name__)

@reputation_bp.route("/api/v1/reputation/summary", methods=["GET"])
@jwt_required()
def get_reputation_summary():
    """Retrieves a reputation summary for the authenticated organization."""
    org_id = get_jwt_identity()["org_id"]
    scores = ReputationScore.query.filter_by(org_id=org_id).all()
    summary = [{"agent_id": score.agent_id, "score": score.score, "signals": score.signals} for score in scores]
    return jsonify(summary)

@reputation_bp.route("/api/v1/reputation/agents", methods=["GET"])
@jwt_required()
def get_agent_reputations():
    """Retrieves a paginated list of agent reputations for the authenticated organization."""
    # Pagination logic to be implemented
    return jsonify([])

