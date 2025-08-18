from flask import Blueprint, request, jsonify, current_app
from src.models.agent import db
from src.models.user import User, UserApiKey, UsageLog
from datetime import datetime
import re

auth_bp = Blueprint('auth', __name__)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"

def authenticate_user(token):
    """Authenticate user by JWT token"""
    if not token:
        return None
    
    if token.startswith('Bearer '):
        token = token[7:]
    
    return User.verify_jwt_token(token, current_app.config['SECRET_KEY'])

def authenticate_api_key(api_key):
    """Authenticate user by API key"""
    if not api_key:
        return None, None
    
    user_api_key = UserApiKey.query.filter_by(api_key=api_key, status='active').first()
    if not user_api_key:
        return None, None
    
    # Update last used timestamp
    user_api_key.last_used = datetime.utcnow()
    db.session.commit()
    
    return user_api_key.user, user_api_key

def log_api_usage(user, api_key, endpoint, method, status_code, response_time_ms, ip_address, user_agent):
    """Log API usage for billing and analytics"""
    usage_log = UsageLog(
        user_id=user.id,
        api_key_id=api_key.id if api_key else None,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        response_time_ms=response_time_ms,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.session.add(usage_log)
    db.session.commit()

@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if field not in data or not data[field].strip():
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate email format
        email = data['email'].lower().strip()
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'User with this email already exists'}), 409
        
        # Validate password
        password = data['password']
        is_valid, message = validate_password(password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Create new user
        user = User(
            email=email,
            first_name=data['first_name'].strip(),
            last_name=data['last_name'].strip(),
            company=data.get('company', '').strip(),
            plan='free'  # Default to free plan
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Generate JWT token
        token = user.generate_jwt_token(current_app.config['SECRET_KEY'])
        
        # Create default API key
        api_key = UserApiKey(
            user_id=user.id,
            key_name='Default API Key',
            api_key=UserApiKey.generate_api_key()
        )
        db.session.add(api_key)
        db.session.commit()
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'token': token,
            'api_key': api_key.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        
        # Find user
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Check if user is active
        if user.status != 'active':
            return jsonify({'error': 'Account is suspended or cancelled'}), 403
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Generate JWT token
        token = user.generate_jwt_token(current_app.config['SECRET_KEY'])
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'token': token
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """User logout (client-side token removal)"""
    return jsonify({'message': 'Logout successful'}), 200

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current user profile"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        user = authenticate_user(auth_header)
        
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api-keys', methods=['GET'])
def get_api_keys():
    """Get user's API keys"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        user = authenticate_user(auth_header)
        
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        api_keys = user.api_keys.filter_by(status='active').all()
        
        return jsonify({
            'api_keys': [key.to_dict() for key in api_keys]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api-keys', methods=['POST'])
def create_api_key():
    """Create a new API key"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        user = authenticate_user(auth_header)
        
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        data = request.get_json()
        key_name = data.get('key_name', 'API Key').strip()
        
        if not key_name:
            return jsonify({'error': 'Key name is required'}), 400
        
        # Check if user already has too many API keys (limit to 5)
        existing_keys = user.api_keys.filter_by(status='active').count()
        if existing_keys >= 5:
            return jsonify({'error': 'Maximum of 5 API keys allowed'}), 400
        
        # Create new API key
        api_key = UserApiKey(
            user_id=user.id,
            key_name=key_name,
            api_key=UserApiKey.generate_api_key()
        )
        
        db.session.add(api_key)
        db.session.commit()
        
        return jsonify({
            'message': 'API key created successfully',
            'api_key': api_key.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api-keys/<key_id>', methods=['DELETE'])
def revoke_api_key(key_id):
    """Revoke an API key"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        user = authenticate_user(auth_header)
        
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Find the API key
        api_key = UserApiKey.query.filter_by(id=key_id, user_id=user.id).first()
        if not api_key:
            return jsonify({'error': 'API key not found'}), 404
        
        # Revoke the key
        api_key.status = 'revoked'
        db.session.commit()
        
        return jsonify({'message': 'API key revoked successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/usage', methods=['GET'])
def get_usage_stats():
    """Get user's usage statistics"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        user = authenticate_user(auth_header)
        
        if not user:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Get query parameters
        days = int(request.args.get('days', 30))
        
        # Calculate date range
        from datetime import datetime, timedelta
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get usage logs
        usage_logs = user.usage_logs.filter(
            UsageLog.created_at >= start_date,
            UsageLog.created_at <= end_date
        ).all()
        
        # Calculate statistics
        total_calls = len(usage_logs)
        successful_calls = len([log for log in usage_logs if log.status_code and log.status_code < 400])
        avg_response_time = sum([log.response_time_ms for log in usage_logs if log.response_time_ms]) / max(total_calls, 1)
        
        # Group by endpoint
        endpoint_stats = {}
        for log in usage_logs:
            endpoint = log.endpoint
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {'count': 0, 'avg_response_time': 0}
            endpoint_stats[endpoint]['count'] += 1
        
        # Group by day
        daily_stats = {}
        for log in usage_logs:
            day = log.created_at.date().isoformat()
            if day not in daily_stats:
                daily_stats[day] = 0
            daily_stats[day] += 1
        
        return jsonify({
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'summary': {
                'total_calls': total_calls,
                'successful_calls': successful_calls,
                'success_rate': (successful_calls / max(total_calls, 1)) * 100,
                'avg_response_time_ms': round(avg_response_time, 2),
                'current_month_usage': user.get_current_usage(),
                'plan_limits': user.get_plan_limits()
            },
            'endpoint_stats': endpoint_stats,
            'daily_stats': daily_stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

