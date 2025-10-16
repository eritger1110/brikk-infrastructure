# -*- coding: utf-8 -*-
"""
Trust Layer Routes (Phase 7).

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


# ==================== ATTESTATIONS CRUD ====================

@trust_bp.route('/attestations', methods=['POST'])
@require_scope('trust:write')
def create_attestation():
    """
    Create a new attestation (vouch for an org or agent).
    
    Requires trust:write scope.
    """
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['subject_type', 'subject_id', 'weight', 'statement']
    missing_fields = [f for f in required_fields if f not in data]
    if missing_fields:
        return jsonify({
            'error': 'missing_fields',
            'message': f'Missing required fields: {", ".join(missing_fields)}',
            'request_id': getattr(g, 'request_id', None)
        }), 400
    
    # Validate subject_type
    if data['subject_type'] not in ['org', 'agent']:
        return jsonify({
            'error': 'invalid_subject_type',
            'message': 'subject_type must be "org" or "agent"',
            'request_id': getattr(g, 'request_id', None)
        }), 400
    
    # Validate weight (0.0-1.0)
    try:
        weight = float(data['weight'])
        if not 0.0 <= weight <= 1.0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({
            'error': 'invalid_weight',
            'message': 'weight must be a number between 0.0 and 1.0',
            'request_id': getattr(g, 'request_id', None)
        }), 400
    
    # Get attester org_id from request context
    attester_org_id = getattr(g, 'org_id', None)
    if not attester_org_id:
        return jsonify({
            'error': 'unauthorized',
            'message': 'Attestations require authenticated organization',
            'request_id': getattr(g, 'request_id', None)
        }), 401
    
    # Prevent self-attestation
    if data['subject_type'] == 'org' and data['subject_id'] == str(attester_org_id):
        return jsonify({
            'error': 'self_attestation',
            'message': 'Organizations cannot attest to themselves',
            'request_id': getattr(g, 'request_id', None)
        }), 400
    
    # Create attestation
    db = next(get_db())
    attestation = Attestation.create_attestation(
        db,
        attester_org_id=str(attester_org_id),
        subject_type=data['subject_type'],
        subject_id=data['subject_id'],
        weight=weight,
        statement=data['statement'],
        evidence_url=data.get('evidence_url')
    )
    
    return jsonify({
        'attestation_id': attestation.id,
        'attester_org_id': attestation.attester_org_id,
        'subject_type': attestation.subject_type,
        'subject_id': attestation.subject_id,
        'weight': attestation.weight,
        'statement': attestation.statement,
        'evidence_url': attestation.evidence_url,
        'created_at': attestation.created_at.isoformat(),
        'request_id': getattr(g, 'request_id', None)
    }), 201


@trust_bp.route('/attestations', methods=['GET'])
def list_attestations():
    """
    List all attestations for a subject (org or agent).
    
    Query params: subject_type, subject_id
    Public endpoint - no auth required.
    """
    subject_type = request.args.get('subject_type')
    subject_id = request.args.get('subject_id')
    
    if not subject_type or not subject_id:
        return jsonify({
            'error': 'missing_parameters',
            'message': 'subject_type and subject_id are required query parameters',
            'request_id': getattr(g, 'request_id', None)
        }), 400
    
    # Validate subject_type
    if subject_type not in ['org', 'agent']:
        return jsonify({
            'error': 'invalid_subject_type',
            'message': 'subject_type must be "org" or "agent"',
            'request_id': getattr(g, 'request_id', None)
        }), 400
    
    db = next(get_db())
    attestations = Attestation.get_attestations(db, subject_type, subject_id)
    
    # Format attestations for response
    attestations_data = [
        {
            'attestation_id': att.id,
            'attester_org_id': att.attester_org_id,
            'weight': att.weight,
            'statement': att.statement,
            'evidence_url': att.evidence_url,
            'created_at': att.created_at.isoformat()
        }
        for att in attestations
    ]
    
    # Compute aggregate trust metrics
    total_weight = sum(att.weight for att in attestations)
    avg_weight = total_weight / len(attestations) if attestations else 0.0
    
    return jsonify({
        'subject_type': subject_type,
        'subject_id': subject_id,
        'attestations': attestations_data,
        'count': len(attestations),
        'total_weight': round(total_weight, 2),
        'avg_weight': round(avg_weight, 2),
        'request_id': getattr(g, 'request_id', None)
    }), 200


@trust_bp.route('/attestations/<attestation_id>', methods=['GET'])
def get_attestation(attestation_id):
    """
    Get a specific attestation by ID.
    
    Public endpoint - no auth required.
    """
    db = next(get_db())
    attestation = db.query(Attestation).filter(Attestation.id == attestation_id).first()
    
    if not attestation:
        return jsonify({
            'error': 'not_found',
            'message': f'Attestation {attestation_id} not found',
            'request_id': getattr(g, 'request_id', None)
        }), 404
    
    return jsonify({
        'attestation_id': attestation.id,
        'attester_org_id': attestation.attester_org_id,
        'subject_type': attestation.subject_type,
        'subject_id': attestation.subject_id,
        'weight': attestation.weight,
        'statement': attestation.statement,
        'evidence_url': attestation.evidence_url,
        'created_at': attestation.created_at.isoformat(),
        'request_id': getattr(g, 'request_id', None)
    }), 200


@trust_bp.route('/attestations/<attestation_id>', methods=['DELETE'])
@require_scope('trust:write')
def revoke_attestation(attestation_id):
    """
    Revoke an attestation.
    
    Only the attester can revoke their own attestation.
    Requires trust:write scope.
    """
    # Get attester org_id from request context
    attester_org_id = getattr(g, 'org_id', None)
    if not attester_org_id:
        return jsonify({
            'error': 'unauthorized',
            'message': 'Attestation revocation requires authenticated organization',
            'request_id': getattr(g, 'request_id', None)
        }), 401
    
    db = next(get_db())
    attestation = db.query(Attestation).filter(Attestation.id == attestation_id).first()
    
    if not attestation:
        return jsonify({
            'error': 'not_found',
            'message': f'Attestation {attestation_id} not found',
            'request_id': getattr(g, 'request_id', None)
        }), 404
    
    # Verify ownership
    if attestation.attester_org_id != str(attester_org_id):
        return jsonify({
            'error': 'forbidden',
            'message': 'You can only revoke your own attestations',
            'request_id': getattr(g, 'request_id', None)
        }), 403
    
    # Delete attestation
    db.delete(attestation)
    db.commit()
    
    return jsonify({
        'message': 'Attestation revoked successfully',
        'attestation_id': attestation_id,
        'request_id': getattr(g, 'request_id', None)
    }), 200


# ==================== RISK EVENTS ====================

@trust_bp.route('/risk-events/<org_id>', methods=['GET'])
@require_scope('admin')
def list_risk_events(org_id):
    """
    List recent risk events for an organization.
    
    Requires admin scope.
    """
    limit = request.args.get('limit', 50, type=int)
    limit = min(limit, 100)  # Cap at 100
    
    db = next(get_db())
    events = db.query(RiskEvent).filter(
        RiskEvent.org_id == org_id
    ).order_by(RiskEvent.created_at.desc()).limit(limit).all()
    
    events_data = [
        {
            'event_id': event.id,
            'type': event.type,
            'severity': event.severity,
            'actor_id': event.actor_id,
            'meta': event.meta,
            'created_at': event.created_at.isoformat()
        }
        for event in events
    ]
    
    return jsonify({
        'org_id': org_id,
        'events': events_data,
        'count': len(events),
        'request_id': getattr(g, 'request_id', None)
    }), 200

