# src/models/user.py
from datetime import datetime, timedelta, timezone
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    password_hash = db.Column(db.String(255), nullable=False)

    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_token = db.Column(db.String(128), index=True, nullable=True)
    verification_expires = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # --- password helpers ---
    def set_password(self, raw_password: str):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    # --- email verification helpers ---
    def issue_verification(self, minutes=60):
        self.verification_token = secrets.token_urlsafe(32)
        self.verification_expires = datetime.now(timezone.utc) + timedelta(minutes=minutes)

    def clear_verification(self):
        self.verification_token = None
        self.verification_expires = None

    # --- safe serializer ---
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
