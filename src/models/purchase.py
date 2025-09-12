# src/models/purchase.py
import datetime as dt
from flask_sqlalchemy import SQLAlchemy
from src.models.agent import db  # reuse the shared SQLAlchemy instance

class Purchase(db.Model):
    """
    Purchases made via Stripe. We store a short alphanumeric `order_ref`
    you can show to users instead of Stripe's long session/subscription ids.
    """
    __tablename__ = "purchases"

    id                    = db.Column(db.Integer, primary_key=True)
    order_ref             = db.Column(db.String(32), unique=True, nullable=False, index=True)
    email                 = db.Column(db.String(255), nullable=False, index=True)
    stripe_customer_id    = db.Column(db.String(64), nullable=True, index=True)
    stripe_subscription_id= db.Column(db.String(64), nullable=True, index=True)
    created_at            = db.Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
