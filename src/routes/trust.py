"""
Trust layer routes for reputation, attestations, and risk management.
"""

from flask import Blueprint, request, jsonify, g
from src.services.auth_middleware import require_auth, require_scope
from src.models.trust import ReputationSnapshot, Attestation, RiskEvent
from src.services.reputation_engine import ReputationEngine
from src.database import db
from datetime import datetime

trust_bp = Blueprint('trust', __name__, url_prefix='/api/v1/trust')


@trust_bp.route('/reputation/<subject_type>/<subject_id>', methods=['GET'])
@require_auth
def get_reputation(subject_type, subject_id):
    """Get reputation score for an org or agent."""
    window_days = request.args.get('window_days', 30, type=int)
    
    snapshot = ReputationSnapshot.get_latest(subject_type, subject_id, window_days)
    
    if not snapshot:
        return jsonify({
            "error": "No reputation data available",
            "subject_type": subject_type,
            "subject_id": subject_id
        }), 404
    
    return jsonify({
        "subject_type": snapshot.subject_type,
        "subject_id": snapshot.subject_id,
        "score": snapshot.score,
        "score_bucket": ReputationEngine.bucket_score(snapshot.score),
        "window_days": snapshot.window_days,
        "components": snapshot.components,
        "computed_at": snapshot.created_at.isoformat()
    })


@trust_bp.route('/attestations', methods=['GET', 'POST'])
@require_auth
def attestations():
    """List or create attestations."""
    if request.method == 'GET':
        subject_type = request.args.get('subject_type')
        subject_id = request.args.get('subject_id')
        
        query = Attestation.query
        
        if subject_type and subject_id:
            query = query.filter_by(subject_type=subject_type, subject_id=subject_id, revoked=False)
        
        attestations = query.order_by(Attestation.created_at.desc()).limit(100).all()
        
        return jsonify({
            "attestations": [{
                "id": att.id,
                "issuer_org_id": att.issuer_org_id,
                "subject_type": att.subject_type,
                "subject_id": att.subject_id,
                "claim": att.claim,
                "score": att.score,
                "created_at": att.created_at.isoformat()
            } for att in attestations]
        })
    
    else:  # POST
        data = request.json
        
        attestation = Attestation(
            issuer_org_id=g.org_id,
            subject_type=data['subject_type'],
            subject_id=data['subject_id'],
            claim=data['claim'],
            score=data.get('score', 80)
        )
        
        db.session.add(attestation)
        db.session.commit()
        
        return jsonify({
            "id": attestation.id,
            "issuer_org_id": attestation.issuer_org_id,
            "subject_type": attestation.subject_type,
            "subject_id": attestation.subject_id,
            "claim": attestation.claim,
            "score": attestation.score,
            "created_at": attestation.created_at.isoformat()
        }), 201

