#!/usr/bin/env python3

import pytest
from flask import Flask
from src.main import create_app
from src.database import db
from src.models.economy import OrgBalance, LedgerAccount, LedgerEntry, Transaction, ReputationScore
from src.models.org import Organization

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret-key"
    })
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_db_migrations(app):
    # Check if all tables were created
    with app.app_context():
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        assert "org_balances" in tables
        assert "ledger_accounts" in tables
        assert "ledger_entries" in tables
        assert "transactions" in tables
        assert "reputation_scores" in tables

def test_system_accounts_seeded(app):
    with app.app_context():
        revenue_account = LedgerAccount.query.filter_by(name="platform_revenue").first()
        fees_account = LedgerAccount.query.filter_by(name="platform_fees").first()
        promotions_account = LedgerAccount.query.filter_by(name="promotions").first()
        assert revenue_account is not None
        assert fees_account is not None
        assert promotions_account is not None

def test_double_entry_invariant(app):
    with app.app_context():
        org = Organization(name="Test Org", slug="test-org")
        db.session.add(org)
        db.session.commit()

        tx = Transaction(
            type="test_transaction",
            org_id=org.id,
            amount=100,
            net_amount=100,
            idempotency_key="test-key"
        )
        db.session.add(tx)
        db.session.commit()

        entry1 = LedgerEntry(tx_id=tx.id, account_id=1, amount=100)
        entry2 = LedgerEntry(tx_id=tx.id, account_id=2, amount=-100)
        db.session.add_all([entry1, entry2])
        db.session.commit()

        entries = LedgerEntry.query.filter_by(tx_id=tx.id).all()
        assert sum(entry.amount for entry in entries) == 0

