# -*- coding: utf-8 -*-
"""Economy and credits management resources."""

from typing import TYPE_CHECKING, Dict, Any, Optional
import uuid

if TYPE_CHECKING:
    from .._http import HTTPClient

from ..types import Transaction


class EconomyResource:
    """Economy and credits management operations."""

    def __init__(self, http_client: "HTTPClient"):
        self._http = http_client

    def get_balance(self, org_id: str) -> int:
        """Get credit balance for an organization.

        Args:
            org_id: Organization ID

        Returns:
            Balance in credits (integer)

        Example:
            >>> balance = client.economy.get_balance("org_123")
            >>> print(f"Balance: {balance} credits")
        """
        response = self._http.get("/api/v1/economy/balance", params={"org_id": org_id})
        return response.get("balance", 0)

    def create_transaction(
        self,
        org_id: str,
        transaction_type: str,
        amount: int,
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Transaction:
        """Create a new transaction.

        Args:
            org_id: Organization ID
            transaction_type: Type of transaction (e.g., "credit", "debit")
            amount: Amount in credits (positive or negative)
            metadata: Optional metadata dict
            idempotency_key: Optional idempotency key for safe retries

        Returns:
            Transaction record

        Example:
            >>> tx = client.economy.create_transaction(
            ...     org_id="org_123",
            ...     transaction_type="credit",
            ...     amount=100,
            ...     metadata={"reason": "monthly_grant"}
            ... )
        """
        data = {
            "org_id": org_id,
            "type": transaction_type,
            "amount": amount,
            "meta": metadata or {},
            "idempotency_key": idempotency_key or str(uuid.uuid4()),
        }
        return self._http.post("/api/v1/economy/transaction", json_data=data)

