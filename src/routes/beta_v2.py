"""
Beta Program Routes (V2 - Bulletproof)
Handles beta application submissions with consistent JSON responses, CORS, validation, and observability
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import secrets
import hashlib
import logging
import re
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

# Set up structured logger
logger = logging.getLogger('beta.apply')
logger.setLevel(logging.INFO)

def log_structured_event(event, application_id=None, email=None, ip_address=None, user_agent=None, status=None, **kwargs):
    """Log structured audit event with consistent fields"""
    # Hash sensitive data
    email_hash = hashlib.sha256(email.encode()).hexdigest()[:16] if email else None
    ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()[:16] if ip_address else None
    user_agent_truncated = user_agent[:100] if user_agent else None
    
    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'event': event,
        'application_id': application_id,
        'email_hash': email_hash,
        'ip_hash': ip_hash,
        'user_agent': user_agent_truncated,
        'status': status,
        **kwargs
    }
    logger.info(f"AUDIT: {log_data}")
    return log_data


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_application_data(data):
    """
    Validate application data and return errors dict
    
    Returns:
        (is_valid: bool, errors: dict)
    """
    errors = {}
    
    # Validate name
    name = data.get('name', '').strip()
    if not name:
        errors['name'] = 'Name is required'
    elif len(name) < 1 or len(name) > 120:
        errors['name'] = 'Name must be between 1 and 120 characters'
    
    # Validate email
    email = data.get('email', '').strip()
    if not email:
        errors['email'] = 'Email is required'
    elif not validate_email(email):
        errors['email'] = 'Invalid email address'
    
    # Validate use_case
    use_case = data.get('use_case', '').strip()
    if not use_case:
        errors['use_case'] = 'Use case is required'
    elif len(use_case) < 1 or len(use_case) > 1000:
        errors['use_case'] = 'Use case must be between 1 and 1000 characters'
    
    # Company is optional, but validate length if provided
    company = data.get('company', '').strip() if data.get('company') else None
    if company and len(company) > 200:
        errors['company'] = 'Company name must be less than 200 characters'
    
    return len(errors) == 0, errors


@bp.route('/apply', methods=['POST', 'OPTIONS'])
@limiter.limit("60 per minute")  # Temporarily increased for testing
def apply_for_beta():
    """
    Submit a beta program application
    
    Public endpoint - no authentication required
    
    Request JSON:
    {
      "name": "string (1..120)",
      "email": "string (valid email)",
      "company": "string|nullable",
      "use_case": "string (1..1000)",
      "referrer": "string|nullable"
    }
    
    Responses:
    - 201: Application received
    - 200: Application already exists (idempotent)
    - 422: Validation error
    - 429: Rate limited
    - 500: Server error
    """
    
    # Handle OPTIONS preflight
    if request.method == 'OPTIONS':
        return '', 204
    
    # Get client info
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    
    try:
        data = request.get_json()
        
        if not data:
            log_structured_event(
                event='submit_received',
                ip_address=ip_address,
                user_agent=user_agent,
                status=400,
                error='No JSON data provided'
            )
            return jsonify({
                'code': 'validation_error',
                'message': 'Please provide application data',
                'errors': {'_form': 'No data provided'}
            }), 422
        
        # Log submission received
        log_structured_event(
            event='submit_received',
            email=data.get('email'),
            ip_address=ip_address,
            user_agent=user_agent,
            status=None
        )
        
        # Validate input
        is_valid, errors = validate_application_data(data)
        if not is_valid:
            log_structured_event(
                event='validation_failed',
                email=data.get('email'),
                ip_address=ip_address,
                user_agent=user_agent,
                status=422,
                errors=errors
            )
            return jsonify({
                'code': 'validation_error',
                'message': 'Please correct the highlighted fields.',
                'errors': errors
            }), 422
        
        # Log validation passed
        log_structured_event(
            event='validated_ok',
            email=data['email'],
            ip_address=ip_address,
            user_agent=user_agent,
            status=None
        )
        
        # Check for duplicate email (idempotent)
        email_normalized = data['email'].lower().strip()
        existing = BetaApplication.query.filter_by(email=email_normalized).first()
        
        if existing:
            # Calculate queue position
            queue_position = BetaApplication.query.filter(
                BetaApplication.status == 'pending',
                BetaApplication.created_at <= existing.created_at
            ).count() if existing.status == 'pending' else None
            
            log_structured_event(
                event='duplicate',
                application_id=existing.id,
                email=existing.email,
                ip_address=ip_address,
                user_agent=user_agent,
                status=200
            )
            
            return jsonify({
                'code': 'application_exists',
                'message': 'We already have your application.',
                'application_id': existing.id,
                'queue_position': queue_position
            }), 200
        
        # Create application
        application = BetaApplication(
            name=data['name'].strip(),
            email=email_normalized,
            company=data.get('company', '').strip() if data.get('company') else None,
            use_case=data['use_case'].strip(),
            source=data.get('referrer', 'direct'),
            ip_address=ip_address,
            user_agent=user_agent,
            status='pending'
        )
        
        db.session.add(application)
        db.session.commit()
        
        # Calculate queue position
        queue_position = BetaApplication.query.filter(
            BetaApplication.status == 'pending',
            BetaApplication.created_at <= application.created_at
        ).count()
        
        # Log application created
        log_structured_event(
            event='application_created',
            application_id=application.id,
            email=application.email,
            ip_address=ip_address,
            user_agent=user_agent,
            status=201,
            queue_position=queue_position
        )
        
        # Send confirmation email
        try:
            email_service = get_email_service()
            email_sent = email_service.send_application_received(
                to_email=application.email,
                name=application.name,
                application_id=application.id,
                queue_position=queue_position
            )
            
            if email_sent:
                log_structured_event(
                    event='email_sent',
                    application_id=application.id,
                    email=application.email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status=None,
                    email_type='application_received'
                )
            else:
                log_structured_event(
                    event='email_failed',
                    application_id=application.id,
                    email=application.email,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status=None,
                    email_type='application_received',
                    error='Email service returned False'
                )
        except Exception as e:
            log_structured_event(
                event='email_failed',
                application_id=application.id,
                email=application.email,
                ip_address=ip_address,
                user_agent=user_agent,
                status=None,
                email_type='application_received',
                error=str(e)
            )
        
        # Return success response
        return jsonify({
            'code': 'application_received',
            'message': 'Thanks! Your application is in the queue.',
            'application_id': application.id,
            'queue_position': queue_position
        }), 201
        
    except Exception as e:
        logger.error(f"Error processing beta application: {str(e)}", exc_info=True)
        log_structured_event(
            event='server_error',
            email=data.get('email') if data else None,
            ip_address=ip_address,
            user_agent=user_agent,
            status=500,
            error=str(e)
        )
        return jsonify({
            'code': 'server_error',
            'message': 'An error occurred processing your application. Please try again.',
            'error': str(e) if request.args.get('debug') else None
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
            'code': 'not_found',
            'message': 'Application not found'
        }), 404
    
    # Calculate queue position if pending
    queue_position = None
    if application.status == 'pending':
        queue_position = BetaApplication.query.filter(
            BetaApplication.status == 'pending',
            BetaApplication.created_at <= application.created_at
        ).count()
    
    return jsonify({
        'code': 'ok',
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
        log_structured_event(
            event='application_approved',
            application_id=application.id,
            email=application.email,
            status=200,
            reviewed_by=reviewed_by
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
        log_structured_event(
            event='application_rejected',
            application_id=application.id,
            email=application.email,
            status=200,
            reviewed_by=reviewed_by
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


@bp.route('/health/email', methods=['GET'])
def health_check_email():
    """
    Health check endpoint for email service
    
    Verifies SendGrid configuration without sending emails
    """
    try:
        email_service = get_email_service()
        
        if not email_service.client:
            return jsonify({
                'email_ready': False,
                'reason': 'SendGrid API key not configured'
            }), 503
        
        if not email_service.from_email:
            return jsonify({
                'email_ready': False,
                'reason': 'From email not configured'
            }), 503
        
        return jsonify({
            'email_ready': True,
            'from_email': email_service.from_email,
            'from_name': email_service.from_name
        }), 200
        
    except Exception as e:
        return jsonify({
            'email_ready': False,
            'reason': str(e)
        }), 503

