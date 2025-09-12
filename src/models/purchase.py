# src/models/purchase.py
import datetime as dt
from flask_sqlalchemy import SQLAlchemy
from src.models.agent import db  # reuse the same db instance

class Purchase(db.Model):
    __tablename__ = "purchases"

    id                     = db.Column(db.Integer, primary_key=True)
    order_ref              = db.Column(db.String(32), unique=True, nullable=False, index=True)
    email                  = db.Column(db.String(255), nullable=False, index=True)
    stripe_customer_id     = db.Column(db.String(64), nullable=True, index=True)
    stripe_subscription_id = db.Column(db.String(64), nullable=True, index=True)
    created_at             = db.Column(db.DateTime, default=dt.datetime.utcnow, nullable=False)
