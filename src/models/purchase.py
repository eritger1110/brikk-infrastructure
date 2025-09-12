# src/models/purchase.py
import datetime as dt
from src.models.agent import db  # reuse the single SQLAlchemy() instance

class Purchase(db.Model):
    """
    Simple purchase/subscription record so we can show a clean order reference
    and map it to the Stripe customer/subscription ids.
    """
    __tablename__ = "purchases"

    id = db.Column(db.Integer, primary_key=True)
    # Human-friendly order reference, unique and indexed (e.g., BRK-7X2K9TQ4M1)
    order_ref = db.Column(db.String(32), unique=True, nullable=False, index=True)

    # Email of the purchaser (helps us find latest order for a user)
    email = db.Column(db.String(255), nullable=False, index=True)

    # Stripe identifiers (nullable to support one-off cases)
    stripe_customer_id = db.Column(db.String(64), nullable=True, index=True)
    stripe_subscription_id = db.Column(db.String(64), nullable=True, index=True)

    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Purchase {self.order_ref} email={self.email}>"
