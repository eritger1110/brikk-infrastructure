"""
Magic Link System for Beta Onboarding
Provides time-limited JWT tokens for developer portal and demo playground access
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import jwt
import secrets
import logging
from src.routes.auth_admin import require_admin_token as require_admin
from prometheus_client import Counter

bp = Blueprint('magic_link', __name__, url_prefix='/api/v1/access')

# Set up logger
logger = logging.getLogger('magic_link')
logger.setLevel(logging.INFO)

# Metrics
magic_link_issued_total = Counter(
    'magic_link_issued_total',
    'Total number of magic links issued',
    ['scope']
)

def get_jwt_config():
    """Get JWT configuration from environment"""
    return {
        'secret': current_app.config.get('JWT_SECRET', secrets.token_urlsafe(32)),
        'issuer': current_app.config.get('JWT_ISSUER', 'brikk'),
        'audience': current_app.config.get('JWT_AUDIENCE', 'brikk-beta'),
        'ttl_minutes': int(current_app.config.get('MAGIC_TTL_MIN', 45)),
        'base_url': current_app.config.get('BASE_URL', 'https://brikk-infrastructure.onrender.com')
    }


def create_magic_token(user_id, email, org_id=None, scopes=None):
    """
    Create a magic link JWT token
    
    Args:
        user_id: User/application ID
        email: User email
        org_id: Organization ID (optional)
        scopes: List of scopes (default: ['demo_portal', 'demo_playground'])
    
    Returns:
        dict: Token and metadata
    """
    config = get_jwt_config()
    
    if scopes is None:
        scopes = ['demo_portal', 'demo_playground']
    
    now = datetime.utcnow()
    exp = now + timedelta(minutes=config['ttl_minutes'])
    
    payload = {
        'sub': str(user_id),
        'email': email,
        'org_id': org_id or f'beta_{user_id}',
        'scopes': scopes,
        'iss': config['issuer'],
        'aud': [config['audience']],  # JWT library expects audience as a list
        'iat': now,
        'exp': exp
    }
    
    token = jwt.encode(payload, config['secret'], algorithm='HS256')
    
    return {
        'token': token,
        'expires_at': exp.isoformat(),
        'ttl_minutes': config['ttl_minutes']
    }


def verify_magic_token(token):
    """
    Verify and decode a magic link JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        dict: Decoded payload or None if invalid
    """
    config = get_jwt_config()
    
    try:
        payload = jwt.decode(
            token,
            config['secret'],
            algorithms=['HS256'],
            issuer=config['issuer'],
            audience=[config['audience']]  # JWT library expects audience as a list
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning('Magic token expired')
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f'Invalid magic token: {str(e)}')
        return None


@bp.route('/magic-link', methods=['POST'])
@require_admin
def create_magic_link():
    """
    Create magic links for developer portal and demo playground
    
    Admin-only endpoint
    
    Request body:
    {
        "user_id": "123",
        "email": "user@example.com",
        "org_id": "beta_org_123",  # optional
        "scopes": ["demo_portal", "demo_playground"]  # optional
    }
    
    Response:
    {
        "success": true,
        "portal_url": "https://api.getbrikk.com/static/dev-portal.html#token=...",
        "playground_url": "https://api.getbrikk.com/static/playground.html#token=...",
        "expires_at": "2025-10-21T12:00:00",
        "ttl_minutes": 45
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        user_id = data.get('user_id')
        email = data.get('email')
        
        if not user_id or not email:
            return jsonify({
                'success': False,
                'error': 'user_id and email are required'
            }), 400
        
        org_id = data.get('org_id')
        scopes = data.get('scopes')
        
        # Create magic token
        token_data = create_magic_token(user_id, email, org_id, scopes)
        token = token_data['token']
        
        # Generate URLs
        config = get_jwt_config()
        base_url = config['base_url']
        
        portal_url = f"{base_url}/static/dev-portal.html#token={token}"
        playground_url = f"{base_url}/static/playground.html#token={token}"
        
        # Increment metrics
        magic_link_issued_total.labels(scope='portal').inc()
        magic_link_issued_total.labels(scope='playground').inc()
        
        # Log event
        logger.info(f"Magic link issued for user {user_id} ({email})")
        
        return jsonify({
            'success': True,
            'portal_url': portal_url,
            'playground_url': playground_url,
            'expires_at': token_data['expires_at'],
            'ttl_minutes': token_data['ttl_minutes']
        })
        
    except Exception as e:
        logger.error(f"Error creating magic link: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/me', methods=['GET'])
def get_user_info():
    """
    Get current user information from magic token
    
    Requires Bearer token in Authorization header
    
    Response:
    {
        "success": true,
        "user": {
            "id": "123",
            "email": "user@example.com",
            "org_id": "beta_org_123",
            "scopes": ["demo_portal", "demo_playground"],
            "expires_at": "2025-10-21T12:00:00"
        }
    }
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': 'Bearer token required'
            }), 401
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Verify token
        payload = verify_magic_token(token)
        
        if not payload:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired token'
            }), 401
        
        return jsonify({
            'success': True,
            'user': {
                'id': payload['sub'],
                'email': payload['email'],
                'org_id': payload['org_id'],
                'scopes': payload['scopes'],
                'expires_at': datetime.fromtimestamp(payload['exp']).isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

