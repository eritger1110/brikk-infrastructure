"""
Phase 7 Error Handling Middleware
Provides consistent error responses for Phase 7 features
"""
from flask import jsonify
from sqlalchemy.exc import OperationalError, ProgrammingError, IntegrityError
from src.infra.log import get_logger

logger = get_logger(__name__)


def register_phase7_error_handlers(app):
    """Register error handlers for Phase 7 features"""
    
    @app.errorhandler(OperationalError)
    def handle_operational_error(e):
        """Handle database operational errors (connection, table not found, etc.)"""
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        # Check if it's a missing table error
        if 'does not exist' in error_msg or 'no such table' in error_msg:
            logger.error(f"Database table not found: {error_msg}")
            return jsonify({
                'error': 'feature_not_ready',
                'message': 'This feature requires database migration. Please contact support.',
                'details': 'Database tables not yet created'
            }), 503
        
        # Generic operational error
        logger.error(f"Database operational error: {error_msg}")
        return jsonify({
            'error': 'database_error',
            'message': 'Database operation failed. Please try again later.'
        }), 503
    
    @app.errorhandler(ProgrammingError)
    def handle_programming_error(e):
        """Handle database programming errors (SQL syntax, schema issues)"""
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        logger.error(f"Database programming error: {error_msg}")
        
        return jsonify({
            'error': 'database_schema_error',
            'message': 'Database schema issue detected. Please contact support.',
            'details': 'Schema mismatch or SQL error'
        }), 500
    
    @app.errorhandler(IntegrityError)
    def handle_integrity_error(e):
        """Handle database integrity errors (foreign key, unique constraint)"""
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        logger.error(f"Database integrity error: {error_msg}")
        
        # Check for specific constraint violations
        if 'foreign key' in error_msg.lower():
            return jsonify({
                'error': 'invalid_reference',
                'message': 'Referenced entity does not exist'
            }), 400
        
        if 'unique' in error_msg.lower() or 'duplicate' in error_msg.lower():
            return jsonify({
                'error': 'duplicate_entry',
                'message': 'This entry already exists'
            }), 409
        
        # Generic integrity error
        return jsonify({
            'error': 'integrity_error',
            'message': 'Data integrity constraint violated'
        }), 400


def create_feature_disabled_response(feature_name: str, status_code: int = 503):
    """
    Create a consistent response for disabled features
    
    Args:
        feature_name: Name of the feature (e.g., 'marketplace', 'analytics')
        status_code: HTTP status code (503 for disabled, 402 for payment required)
    
    Returns:
        Tuple of (response, status_code)
    """
    messages = {
        503: f'{feature_name.title()} feature is not enabled',
        402: f'{feature_name.title()} feature requires a paid plan',
        403: f'You do not have permission to access {feature_name}'
    }
    
    return jsonify({
        'error': f'{feature_name}_disabled',
        'message': messages.get(status_code, f'{feature_name.title()} is not available'),
        'feature': feature_name,
        'enabled': False
    }), status_code


def create_auth_required_response():
    """Create a consistent authentication required response"""
    return jsonify({
        'error': 'auth_required',
        'message': 'Authentication required. Please provide valid credentials.',
        'hint': 'Include X-User-ID or Authorization header'
    }), 401


def create_validation_error_response(message: str, field: str = None):
    """Create a consistent validation error response"""
    response = {
        'error': 'validation_error',
        'message': message
    }
    if field:
        response['field'] = field
    
    return jsonify(response), 400

