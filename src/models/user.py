from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
import secrets
import jwt
from src.models.agent import db

class User(db.Model):
    """User accounts for the Brikk platform"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    company = db.Column(db.String(100))
    plan = db.Column(db.String(20), default='free')  # free, hacker, starter, professional, enterprise
    status = db.Column(db.String(20), default='active')  # active, suspended, cancelled
    stripe_customer_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    email_verified = db.Column(db.Boolean, default=False)
    
    # Relationships
    api_keys = db.relationship('UserApiKey', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    usage_logs = db.relationship('UsageLog', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    subscriptions = db.relationship('Subscription', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def generate_jwt_token(self, secret_key, expires_in=3600):
        """Generate JWT token for authentication"""
        payload = {
            'user_id': self.id,
            'email': self.email,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, secret_key, algorithm='HS256')
    
    @staticmethod
    def verify_jwt_token(token, secret_key):
        """Verify JWT token and return user"""
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            return User.query.get(payload['user_id'])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_plan_limits(self):
        """Get plan limits for API usage"""
        limits = {
            'free': {'api_calls': 1000, 'agents': 2, 'support': 'community'},
            'hacker': {'api_calls': 7500, 'agents': 3, 'support': 'email'},
            'starter': {'api_calls': 10000, 'agents': 5, 'support': 'email'},
            'professional': {'api_calls': 100000, 'agents': 25, 'support': 'phone'},
            'enterprise': {'api_calls': -1, 'agents': -1, 'support': 'dedicated'}  # -1 = unlimited
        }
        return limits.get(self.plan, limits['free'])
    
    def get_current_usage(self):
        """Get current month's usage"""
        from datetime import datetime
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        usage = db.session.query(db.func.count(UsageLog.id)).filter(
            UsageLog.user_id == self.id,
            UsageLog.created_at >= start_of_month
        ).scalar()
        
        return usage or 0
    
    def can_make_api_call(self):
        """Check if user can make another API call"""
        limits = self.get_plan_limits()
        if limits['api_calls'] == -1:  # Unlimited
            return True
        
        current_usage = self.get_current_usage()
        return current_usage < limits['api_calls']
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'company': self.company,
            'plan': self.plan,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'email_verified': self.email_verified,
            'plan_limits': self.get_plan_limits(),
            'current_usage': self.get_current_usage()
        }
        
        if include_sensitive:
            data['stripe_customer_id'] = self.stripe_customer_id
        
        return data

class UserApiKey(db.Model):
    """API keys for users to access the Brikk platform"""
    __tablename__ = 'user_api_keys'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    key_name = db.Column(db.String(100), nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), default='active')  # active, revoked
    last_used = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserApiKey {self.key_name} for {self.user_id}>'
    
    @staticmethod
    def generate_api_key():
        """Generate a secure API key"""
        return f"brikk_{secrets.token_urlsafe(32)}"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'key_name': self.key_name,
            'api_key': self.api_key,
            'status': self.status,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class UsageLog(db.Model):
    """Log API usage for billing and analytics"""
    __tablename__ = 'usage_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    api_key_id = db.Column(db.String(36), db.ForeignKey('user_api_keys.id'))
    endpoint = db.Column(db.String(200), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    status_code = db.Column(db.Integer)
    response_time_ms = db.Column(db.Integer)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<UsageLog {self.endpoint} for {self.user_id}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'endpoint': self.endpoint,
            'method': self.method,
            'status_code': self.status_code,
            'response_time_ms': self.response_time_ms,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Subscription(db.Model):
    """Stripe subscription management"""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    stripe_subscription_id = db.Column(db.String(100), unique=True, nullable=False)
    stripe_customer_id = db.Column(db.String(100), nullable=False)
    plan = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # active, canceled, past_due, etc.
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Subscription {self.plan} for {self.user_id}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'stripe_subscription_id': self.stripe_subscription_id,
            'plan': self.plan,
            'status': self.status,
            'current_period_start': self.current_period_start.isoformat() if self.current_period_start else None,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'cancel_at_period_end': self.cancel_at_period_end,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

