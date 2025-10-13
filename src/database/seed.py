from src.database.db import db
from src.models.economy import LedgerAccount

def seed_system_accounts():
    """Seeds the database with system ledger accounts."""
    system_accounts = [
        {"name": "platform_revenue", "type": "revenue"},
        {"name": "platform_fees", "type": "fees"},
        {"name": "promotions", "type": "promotions"}
    ]

    for account_data in system_accounts:
        account = LedgerAccount.query.filter_by(name=account_data["name"]).first()
        if not account:
            new_account = LedgerAccount(**account_data)
            db.session.add(new_account)
    
    db.session.commit()

