from functools import wraps
from flask import request, jsonify, g
from src.models.user import User, UserApiKey, UsageLog
from src.routes.auth import authenticate_api_key, log_api_usage
import time

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        # Get API key from header
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        # Authenticate user
        user, user_api_key = authenticate_api_key(api_key)
        if not user:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Check rate limits
        if not user.can_make_api_call():
            limits = user.get_plan_limits()
            return jsonify({
                'error': 'Rate limit exceeded',
                'plan': user.plan,
                'limit': limits['api_calls'],
                'current_usage': user.get_current_usage()
            }), 429
        
        # Store user in request context
        g.current_user = user
        g.current_api_key = user_api_key
        g.request_start_time = start_time
        
        # Execute the function
        response = f(*args, **kwargs)
        
        # Log API usage
        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)
        
        # Get status code from response
        if hasattr(response, 'status_code'):
            status_code = response.status_code
        elif isinstance(response, tuple) and len(response) > 1:
            status_code = response[1]
        else:
            status_code = 200
        
        log_api_usage(
            user=user,
            api_key=user_api_key,
            endpoint=request.endpoint or request.path,
            method=request.method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        return response
    
    return decorated_function

def require_user_auth(f):
    """Decorator to require JWT token authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header required'}), 401
        
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Invalid authorization header format'}), 401
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Verify token
        from flask import current_app
        user = User.verify_jwt_token(token, current_app.config['SECRET_KEY'])
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Store user in request context
        g.current_user = user
        
        return f(*args, **kwargs)
    
    return decorated_function

def optional_auth(f):
    """Decorator for optional authentication (user or API key)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Try JWT token first
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            from flask import current_app
            user = User.verify_jwt_token(token, current_app.config['SECRET_KEY'])
            if user:
                g.current_user = user
                g.auth_type = 'jwt'
                return f(*args, **kwargs)
        
        # Try API key
        api_key = request.headers.get('X-API-Key')
        if api_key:
            user, user_api_key = authenticate_api_key(api_key)
            if user:
                g.current_user = user
                g.current_api_key = user_api_key
                g.auth_type = 'api_key'
                return f(*args, **kwargs)
        
        # No authentication
        g.current_user = None
        g.auth_type = None
        return f(*args, **kwargs)
    
    return decorated_function

