"""
Economy Service

Handles all business logic related to the internal credits ledger, including
transactions, balance management, and double-entry accounting.
"""

import uuid
from sqlalchemy.exc import IntegrityError
from src.database.db import db
from src.models.economy import OrgBalance, LedgerAccount, LedgerEntry, Transaction

class EconomyService:

    def get_balance(self, org_id: str) -> int:
        """Retrieves the current credit balance for a given organization."""
        balance = OrgBalance.query.filter_by(org_id=org_id).first()
        return balance.current_credits if balance else 0

    def ensure_org_balance_row(self, org_id: str) -> OrgBalance:
        """Ensures that an organization has a balance row in the database."""
        balance = OrgBalance.query.filter_by(org_id=org_id).first()
        if not balance:
            balance = OrgBalance(org_id=org_id)
            db.session.add(balance)
            db.session.commit()
        return balance

    def post_transaction(self, org_id: str, type: str, amount: int, meta: dict, idempotency_key: str, system_account: str = 'platform_revenue') -> Transaction:
        """Posts a new transaction to the ledger, ensuring idempotency and atomicity."""
        # Check for existing transaction with the same idempotency key
        existing_tx = Transaction.query.filter_by(idempotency_key=idempotency_key).first()
        if existing_tx:
            return existing_tx

        # Ensure the organization has a balance row
        self.ensure_org_balance_row(org_id)

        # Create a new transaction
        new_tx = Transaction(
            id=str(uuid.uuid4()),
            org_id=org_id,
            type=type,
            amount=abs(amount),
            net_amount=amount,
            idempotency_key=idempotency_key,
            meta=meta
        )

        # Create ledger entries for double-entry accounting
        org_wallet = LedgerAccount.query.filter_by(org_id=org_id, type='org_wallet').first()
        if not org_wallet:
            org_wallet = LedgerAccount(org_id=org_id, name=f"{org_id} Wallet", type='org_wallet')
            db.session.add(org_wallet)

        system_ledger_account = LedgerAccount.query.filter_by(name=system_account, org_id=None).first()

        # Debit/Credit logic
        debit_account = org_wallet if amount < 0 else system_ledger_account
        credit_account = system_ledger_account if amount < 0 else org_wallet

        debit_entry = LedgerEntry(tx_id=new_tx.id, account_id=debit_account.id, amount=-abs(amount))
        credit_entry = LedgerEntry(tx_id=new_tx.id, account_id=credit_account.id, amount=abs(amount))

        try:
            db.session.begin_nested()
            db.session.add(new_tx)
            db.session.add_all([debit_entry, credit_entry])

            # Update organization balance
            balance = OrgBalance.query.filter_by(org_id=org_id).with_for_update().one()
            if balance.current_credits + amount < 0:
                raise ValueError("Insufficient credits")
            balance.current_credits += amount
            
            new_tx.status = 'posted'
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

        return new_tx

