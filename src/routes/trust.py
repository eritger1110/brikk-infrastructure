# -*- coding: utf-8 -*-
"""
Trust Layer Routes (Phase 7 PR-1 stub).

Reputation, attestations, and risk management endpoints.
"""
from flask import Blueprint, jsonify, request, g
from src.services.auth_middleware import require_scope
from src.models.trust import ReputationSnapshot, Attestation, RiskEvent
from src.schemas.trust_schemas import (
    ReputationResponseSchema,
    AttestationCreateSchema,
    AttestationResponseSchema,
    AttestationListResponseSchema
)
from src.services.reputation_engine import ReputationEngine
from src.database import get_db

trust_bp = Blueprint('trust', __name__, url_prefix='/v1/trust')


@trust_bp.route('/reputation/<subject_type>/<subject_id>', methods=['GET'])
def get_reputation(subject_type, subject_id):
    """
    Get reputation score for an org or agent.
    
    Returns bucketed score for privacy (e.g., 80-90) with top factors.
    """
    # Validate subject_type
    if subject_type not in ['org', 'agent']:
        return jsonify({
            'error': 'invalid_subject_type',
            'message': 'subject_type must be "org" or "agent"',
            'request_id': getattr(g, 'request_id', None)
        }), 400
    
    window = request.args.get('window', '30d')
    if window not in ['7d', '30d', '90d']:
        return jsonify({
            'error': 'invalid_window',
            'message': 'window must be "7d", "30d", or "90d"',
            'request_id': getattr(g, 'request_id', None)
        }), 400
    
    db = next(get_db())
    engine = ReputationEngine(db)
    
    # Check for cached snapshot first
    snapshot = ReputationSnapshot.get_latest(db, subject_type, subject_id, window)
    
    if snapshot:
        # Use cached snapshot
        score = snapshot.score
        reason = snapshot.reason
        last_updated = snapshot.created_at
    else:
        # Compute on-demand
        score, reason = engine.compute_score(subject_type, subject_id, window)
        last_updated = None
    
    # Bucket score for privacy
    score_bucket = engine.bucket_score(score)
    
    # Get top 3 factors
    top_factors = engine.get_top_factors(reason, limit=3)
    
    return jsonify({
        'subject_type': subject_type,
        'subject_id': subject_id,
        'score_bucket': score_bucket,
        'window': window,
        'top_factors': top_factors,
        'last_updated': last_updated.isoformat() if last_updated else None,
        'request_id': getattr(g, 'request_id', None)
    }), 200


@trust_bp.route('/reputation/recompute', methods=['POST'])
@require_scope('admin')
def recompute_reputation():
    """
    Trigger batch reputation recomputation.
    
    Requires admin scope.
    """
    window = request.args.get('window', '30d')
    subject_type = request.args.get('subject_type')
    subject_id = request.args.get('subject_id')
    
    if window not in ['7d', '30d', '90d']:
        return jsonify({
            'error': 'invalid_window',
            'message': 'window must be "7d", "30d", or "90d"',
            'request_id': getattr(g, 'request_id', None)
        }), 400
    
    db = next(get_db())
    engine = ReputationEngine(db)
    
    # Recompute (batch or specific subject)
    results = engine.recompute_all(window, subject_type, subject_id)
    
    return jsonify({
        'message': f'Reputation recompute completed for window: {window}',
        'window': window,
        'subject_type': subject_type,
        'subject_id': subject_id,
        'computed_count': len(results),
        'request_id': getattr(g, 'request_id', None)
    }), 200


@trust_bp.route('/attestations', methods=['GET'])
def list_attestations():
    """
    List attestations for a subject.
    
    Query params: subject_type, subject_id
    """
    # Stub implementation - will be completed in PR-4
    subject_type = request.args.get('subject_type')
    subject_id = request.args.get('subject_id')
    
    if not subject_type or not subject_id:
        return jsonify({
            'error': 'missing_parameters',
            'message': 'subject_type and subject_id are required',
            'request_id': getattr(g, 'request_id', None)
        }), 400
    
    return jsonify({
        'attestations': [],
        'total': 0,
        'subject_type': subject_type,
        'subject_id': subject_id,
        'message': 'Attestations CRUD not yet implemented (PR-4)',
        'request_id': getattr(g, 'request_id', None)
    }), 200


@trust_bp.route('/attestations', methods=['POST'])
@require_scope('trust:write')
def create_attestation():
    """
    Create a new attestation.
    
    Requires trust:write scope.
    """
    # Stub implementation - will be completed in PR-4
    return jsonify({
        'message': 'Attestation creation not yet implemented (PR-4)',
        'request_id': getattr(g, 'request_id', None)
    }), 501


@trust_bp.route('/attestations/<attestation_id>', methods=['DELETE'])
@require_scope('trust:write')
def delete_attestation(attestation_id):
    """
    Delete an attestation.
    
    Requires trust:write scope and issuer ownership.
    """
    # Stub implementation - will be completed in PR-4
    return jsonify({
        'message': 'Attestation deletion not yet implemented (PR-4)',
        'request_id': getattr(g, 'request_id', None)
    }), 501

