"""
Usage Statistics API
Provides usage data for authenticated users
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import logging
import secrets
import hashlib
from src.routes.magic_link import verify_magic_token

bp = Blueprint('usage', __name__, url_prefix='/api/v1/usage')

# Set up logger
logger = logging.getLogger('usage')
logger.setLevel(logging.INFO)


def require_magic_token(f):
    """Decorator to require valid magic token"""
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': 'Bearer token required'
            }), 401
        
        token = auth_header[7:]
        payload = verify_magic_token(token)
        
        if not payload:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired token'
            }), 401
        
        # Attach user info to request
        request.user = payload
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function


@bp.route('/me', methods=['GET'])
@require_magic_token
def get_my_usage():
    """
    Get usage statistics for the authenticated user
    
    Requires Bearer token in Authorization header
    
    Response:
    {
        "success": true,
        "usage": {
            "api_calls_today": 42,
            "api_calls_this_month": 1337,
            "total_api_calls": 5000,
            "agents_used": 3,
            "last_call_at": "2025-10-21T10:30:00",
            "quota": {
                "daily_limit": 1000,
                "monthly_limit": 10000,
                "remaining_today": 958,
                "remaining_month": 8663
            }
        }
    }
    """
    try:
        user_id = request.user['sub']
        
        # TODO: Replace with actual database queries
        # For now, return mock data for demo purposes
        usage_data = {
            'api_calls_today': 42,
            'api_calls_this_month': 1337,
            'total_api_calls': 5000,
            'agents_used': 3,
            'last_call_at': (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            'quota': {
                'daily_limit': 1000,
                'monthly_limit': 10000,
                'remaining_today': 958,
                'remaining_month': 8663
            }
        }
        
        logger.info(f"Usage stats requested for user {user_id}")
        
        return jsonify({
            'success': True,
            'usage': usage_data
        })
        
    except Exception as e:
        logger.error(f"Error getting usage stats: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api-key', methods=['GET'])
@require_magic_token
def get_or_create_api_key():
    """
    Get or create an API key for the authenticated user
    
    Requires Bearer token in Authorization header
    
    Response:
    {
        "success": true,
        "api_key": "sk_beta_...",
        "created_at": "2025-10-22T10:30:00",
        "note": "This key is for demo purposes only. Keep it secure!"
    }
    """
    try:
        user_id = request.user['sub']
        email = request.user['email']
        
        # For magic link users, generate a demo API key
        # In production, this would be stored in the database
        # For now, we'll generate a deterministic key based on user_id
        
        # Use a deterministic seed for demo purposes
        # In production, store this in the database
        seed = f"demo_api_key_{user_id}_{email}"
        key_hash = hashlib.sha256(seed.encode()).hexdigest()[:32]
        api_key = f"sk_beta_{key_hash}"
        
        logger.info(f"API key generated/retrieved for user {user_id}")
        
        return jsonify({
            'success': True,
            'api_key': api_key,
            'created_at': datetime.utcnow().isoformat(),
            'note': 'This key is for demo purposes only. Keep it secure!'
        })
        
    except Exception as e:
        logger.error(f"Error getting API key: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

