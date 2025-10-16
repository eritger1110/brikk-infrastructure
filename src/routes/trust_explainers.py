# -*- coding: utf-8 -*-
"""
Trust Layer Explainers (Phase 7 PR-6).

Provides human-readable explanations for reputation scores and risk assessments.
"""
from flask import Blueprint, jsonify, request, g
from src.services.auth_middleware import require_scope
from src.services.reputation_engine import ReputationEngine
from src.database import get_db

trust_explainers_bp = Blueprint(
    'trust_explainers',
    __name__,
    url_prefix='/v1/trust/explainers'
)


@trust_explainers_bp.route(
    '/reputation/<subject_type>/<subject_id>'
    , methods=["GET"]
)
@require_scope("trust:read")
def explain_reputation(subject_type, subject_id):
    """
    Provide a detailed explanation of a reputation score.
    
    Requires trust:read scope.
    """
    # Get org_id from authenticated context
    org_id = getattr(g, 'org_id', None)
    if not org_id:
        return jsonify({
            'error': 'forbidden',
            'message': 'Organization context required',
            'request_id': getattr(g, 'request_id', None)
        }), 403
    
    # Validate subject_type
    if subject_type not in ["org", "agent"]:
        return jsonify({
            'error': 'invalid_subject_type',
            'message': 'subject_type must be "org" or "agent"',
            'request_id': getattr(g, 'request_id', None)
        }), 400
    
    # For now, only allow orgs to explain their own reputation
    if subject_type == 'org' and subject_id != str(org_id):
        return jsonify({
            'error': 'forbidden',
            'message': 'You can only view detailed explanations for your own organization
            ',
            'request_id': getattr(g, 'request_id', None)
        }), 403
    
    window = request.args.get('window', '30d')
    if window not in ["7d", "30d", "90d"]:
        return jsonify({
            'error': 'invalid_window',
            'message': 'window must be "7d", "30d", or "90d"',
            'request_id': getattr(g, 'request_id', None)
        }), 400
    
    db = next(get_db())
    engine = ReputationEngine(db)
    
    # Compute score and get detailed reason
    score, reason = engine.compute_score(subject_type, subject_id, window)
    
    return jsonify({
        'subject_type': subject_type,
        'subject_id': subject_id,
        'window': window,
        'score': round(score, 2),
        'explanation': reason,
        'request_id': getattr(g, 'request_id', None)
    }), 200

