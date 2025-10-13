'''
Economy and Reputation Models

Defines the database schema for the internal credits ledger, transactions,
and agent reputation system.
'''

import uuid
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, Numeric, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database import db

class OrgBalance(db.Model):
    __tablename__ = "org_balances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, unique=True, index=True)
    current_credits = Column(BigInteger, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="balance")

class LedgerAccount(db.Model):
    __tablename__ = "ledger_accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=True)
    name = Column(String(64), nullable=False)
    type = Column(String(32), nullable=False)  # e.g., org_wallet, fees, revenue, promotions
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LedgerEntry(db.Model):
    __tablename__ = "ledger_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tx_id = Column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey("ledger_accounts.id"), nullable=False, index=True)
    amount = Column(BigInteger, nullable=False)  # Signed integer
    currency = Column(String(16), default='CRD')
    memo = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

class Transaction(db.Model):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(32), nullable=False)  # top_up, coordination_charge, refund, promo_bonus
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    amount = Column(BigInteger, nullable=False)  # Absolute value
    net_amount = Column(BigInteger, nullable=False)
    status = Column(String(16), default='pending')  # pending, posted, failed, refunded
    idempotency_key = Column(String(64), unique=True, nullable=False)
    external_ref = Column(String(128), nullable=True)
    meta = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)

    entries = relationship("LedgerEntry", backref="transaction", cascade="all, delete-orphan")

class ReputationScore(db.Model):
    __tablename__ = "reputation_scores"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True, index=True)
    score = Column(Numeric(5, 2), nullable=False, default=50.00)
    weight = Column(Numeric(5, 2), nullable=False, default=1.00)
    signals = Column(JSON)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), index=True)

    organization = relationship("Organization", back_populates="reputation_scores")
    agent = relationship("Agent", back_populates="reputation_scores")

