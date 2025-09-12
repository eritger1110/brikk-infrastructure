# src/models/user.py
from datetime import datetime, timedelta, timezone
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from src.database.db import db                       # ← single shared db

class User(db.Model):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80),  unique=True, nullable=False, index=True)
    email    = db.Column(db.String(120), unique=True, nullable=False, index=True)

    password_hash = db.Column(db.String(255), nullable=False)

    email_verified       = db.Column(db.Boolean, default=False, nullable=False)
    verification_token   = db.Column(db.String(128), index=True, nullable=True)
    verification_expires = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Helpers
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # Email verification helpers
    def start_email_verification(self, minutes: int = 60) -> str:
        token = secrets.token_urlsafe(32)
        self.verification_token = token
        self.verification_expires = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        return token

    def verify_email_with(self, token: str) -> bool:
        if (
            self.verification_token
            and self.verification_token == token
            and self.verification_expires
            and datetime.now(timezone.utc) <= self.verification_expires
        ):
            self.email_verified = True
            self.verification_token = None
            self.verification_expires = None
            return True
        return False
