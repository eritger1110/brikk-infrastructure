"""
Beta Program Routes
Handles beta application submissions, admin review, and invitation management
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import secrets
import hashlib
import logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from src.infra.db import db
from src.models.beta_application import BetaApplication
from src.models.api_key import ApiKey
from src.routes.auth_admin import require_admin_token as require_admin
from src.services.email_service import get_email_service

# Temporary: No auth required for public submission endpoint
def require_auth(f):
    return f

bp = Blueprint('beta', __name__, url_prefix='/api/v1/beta')

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per hour"],
    storage_uri="memory://"
)

# Set up audit logger
audit_logger = logging.getLogger('beta_audit')
audit_logger.setLevel(logging.INFO)

def log_audit_event(action, application_id=None, user=None, metadata=None):
    """Log structured audit event"""
    event = {
        'timestamp': datetime.utcnow().isoformat(),
        'action': action,
        'application_id': application_id,
        'user': user,
        'metadata': metadata or {}
    }
    audit_logger.info(f"AUDIT: {event}")
    return event


@bp.route('/applications', methods=['POST'])
@limiter.limit("10 per minute")
def submit_application():
    """
    Submit a beta program application
    
    Public endpoint - no authentication required
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'use_case']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Check for duplicate email
        existing = BetaApplication.query.filter_by(email=data['email'].lower()).first()
        if existing:
            return jsonify({
                'success': False,
                'error': 'An application with this email already exists',
                'status': existing.status,
                'application_id': existing.id
            }), 409
        
        # Get client info
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        source = data.get('source', 'direct')
        
        # Create application
        application = BetaApplication(
            name=data['name'].strip(),
            email=data['email'].lower().strip(),
            company=data.get('company', '').strip() if data.get('company') else None,
            use_case=data['use_case'].strip(),
            source=source,
            ip_address=ip_address,
            user_agent=user_agent,
            status='pending'
        )
        
        db.session.add(application)
        db.session.commit()
        
        # Log audit event
        log_audit_event(
            action='application_submitted',
            application_id=application.id,
            metadata={
                'email': application.email,
                'source': source,
                'ip_address': ip_address
            }
        )
        
        # Send confirmation email
        email_service = get_email_service()
        email_service.send_application_received(
            to_email=application.email,
            name=application.name,
            application_id=application.id,
            queue_position=BetaApplication.query.filter(
                BetaApplication.status == 'pending',
                BetaApplication.created_at <= application.created_at
            ).count()
        )
        
        # Get queue position
        queue_position = BetaApplication.query.filter(
            BetaApplication.status == 'pending',
            BetaApplication.created_at <= application.created_at
        ).count()
        
        return jsonify({
            'success': True,
            'message': 'Application submitted successfully',
            'application_id': application.id,
            'queue_position': queue_position,
            'estimated_review_time': '24-48 hours'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/applications/<int:application_id>/status', methods=['GET'])
def get_application_status(application_id):
    """
    Check the status of a beta application
    
    Public endpoint - returns limited info
    """
    application = BetaApplication.query.get(application_id)
    
    if not application:
        return jsonify({
            'success': False,
            'error': 'Application not found'
        }), 404
    
    # Calculate queue position if pending
    queue_position = None
    if application.status == 'pending':
        queue_position = BetaApplication.query.filter(
            BetaApplication.status == 'pending',
            BetaApplication.created_at <= application.created_at
        ).count()
    
    return jsonify({
        'success': True,
        'application': {
            'id': application.id,
            'status': application.status,
            'created_at': application.created_at.isoformat(),
            'queue_position': queue_position
        }
    })


@bp.route('/admin/applications', methods=['GET'])
@require_admin
def list_applications():
    """
    List all beta applications (admin only)
    
    Query params:
    - status: filter by status (pending, approved, rejected, invited)
    - limit: number of results (default 50)
    - offset: pagination offset (default 0)
    """
    status = request.args.get('status')
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    
    query = BetaApplication.query
    
    if status:
        query = query.filter_by(status=status)
    
    # Order by created_at desc
    query = query.order_by(BetaApplication.created_at.desc())
    
    total = query.count()
    applications = query.limit(limit).offset(offset).all()
    
    return jsonify({
        'success': True,
        'total': total,
        'limit': limit,
        'offset': offset,
        'applications': [app.to_dict() for app in applications]
    })


@bp.route('/admin/applications/<int:application_id>/approve', methods=['POST'])
@require_admin
def approve_application(application_id):
    """
    Approve a beta application and generate API key
    
    Admin only
    """
    try:
        application = BetaApplication.query.get(application_id)
        
        if not application:
            return jsonify({
                'success': False,
                'error': 'Application not found'
            }), 404
        
        if application.status != 'pending':
            return jsonify({
                'success': False,
                'error': f'Application is already {application.status}'
            }), 400
        
        # Generate API key
        api_key = 'sk_beta_' + secrets.token_urlsafe(32)
        
        # Update application
        application.status = 'approved'
        application.reviewed_at = datetime.utcnow()
        reviewed_by = request.user.email if hasattr(request, 'user') else 'admin'
        application.reviewed_by = reviewed_by
        application.api_key = hashlib.sha256(api_key.encode()).hexdigest()
        
        data = request.get_json() or {}
        if data.get('admin_notes'):
            application.admin_notes = data['admin_notes']
        
        db.session.commit()
        
        # Log audit event
        log_audit_event(
            action='application_approved',
            application_id=application.id,
            user=reviewed_by,
            metadata={
                'email': application.email,
                'admin_notes': data.get('admin_notes')
            }
        )
        
        # Send approval email with API key
        email_service = get_email_service()
        email_service.send_application_approved(
            to_email=application.email,
            name=application.name,
            api_key=api_key,
            application_id=application.id
        )
        
        return jsonify({
            'success': True,
            'message': 'Application approved',
            'application': application.to_dict(),
            'api_key': api_key  # Only returned once!
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/admin/applications/<int:application_id>/reject', methods=['POST'])
@require_admin
def reject_application(application_id):
    """
    Reject a beta application
    
    Admin only
    """
    try:
        application = BetaApplication.query.get(application_id)
        
        if not application:
            return jsonify({
                'success': False,
                'error': 'Application not found'
            }), 404
        
        if application.status != 'pending':
            return jsonify({
                'success': False,
                'error': f'Application is already {application.status}'
            }), 400
        
        # Update application
        application.status = 'rejected'
        application.reviewed_at = datetime.utcnow()
        reviewed_by = request.user.email if hasattr(request, 'user') else 'admin'
        application.reviewed_by = reviewed_by
        
        data = request.get_json() or {}
        if data.get('admin_notes'):
            application.admin_notes = data['admin_notes']
        
        db.session.commit()
        
        # Log audit event
        log_audit_event(
            action='application_rejected',
            application_id=application.id,
            user=reviewed_by,
            metadata={
                'email': application.email,
                'admin_notes': data.get('admin_notes')
            }
        )
        
        # Send polite rejection email
        email_service = get_email_service()
        email_service.send_application_rejected(
            to_email=application.email,
            name=application.name,
            application_id=application.id
        )
        
        return jsonify({
            'success': True,
            'message': 'Application rejected',
            'application': application.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/admin/stats', methods=['GET'])
@require_admin
def get_beta_stats():
    """
    Get beta program statistics
    
    Admin only
    """
    try:
        total = BetaApplication.query.count()
        pending = BetaApplication.query.filter_by(status='pending').count()
        approved = BetaApplication.query.filter_by(status='approved').count()
        rejected = BetaApplication.query.filter_by(status='rejected').count()
        invited = BetaApplication.query.filter_by(status='invited').count()
        
        # Recent applications (last 7 days)
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent = BetaApplication.query.filter(
            BetaApplication.created_at >= week_ago
        ).count()
        
        # Top use cases
        use_cases = db.session.query(
            BetaApplication.use_case,
            db.func.count(BetaApplication.id).label('count')
        ).group_by(BetaApplication.use_case).order_by(db.text('count DESC')).limit(10).all()
        
        # Top sources
        sources = db.session.query(
            BetaApplication.source,
            db.func.count(BetaApplication.id).label('count')
        ).group_by(BetaApplication.source).order_by(db.text('count DESC')).limit(10).all()
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'by_status': {
                    'pending': pending,
                    'approved': approved,
                    'rejected': rejected,
                    'invited': invited
                },
                'recent_7_days': recent,
                'top_use_cases': [{'use_case': uc, 'count': count} for uc, count in use_cases],
                'top_sources': [{'source': src or 'direct', 'count': count} for src, count in sources]
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

