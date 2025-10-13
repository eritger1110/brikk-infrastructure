# src/models/purchase.py
import datetime as dt
from src.database import db

class Purchase(db.Model):
    __tablename__ = "purchases"
    __table_args__ = {"extend_existing": True}  # <-- important

    id                     = db.Column(db.Integer, primary_key=True)
    order_ref              = db.Column(db.String(32), unique=True, nullable=False, index=True)
    email                  = db.Column(db.String(255), nullable=False, index=True)
    stripe_customer_id     = db.Column(db.String(64),  nullable=True, index=True)
    stripe_subscription_id = db.Column(db.String(64),  nullable=True, index=True)
    created_at             = db.Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
