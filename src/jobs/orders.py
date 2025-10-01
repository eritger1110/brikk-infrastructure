# src/jobs/orders.py
from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Tuple, Callable, Optional

import requests
from requests.adapters import HTTPAdapter, Retry

try:
    # Available in RQ workers; safe no-op in web context
    from rq import get_current_job  # type: ignore
except Exception:  # pragma: no cover
    def get_current_job():
        return None  # type: ignore

# If SQLAlchemy is available we can persist a lightweight row.
# This is optional—will no-op if the table doesn't exist.
try:
    from sqlalchemy import inspect, text  # type: ignore
    from src.database.db import db  # type: ignore
except Exception:  # pragma: no cover
    db = None  # type: ignore
    inspect = None  # type: ignore
    text = None  # type: ignore


# ------------------------
# Utilities
# ------------------------

JSON = Dict[str, Any]


def _requests_session() -> requests.Session:
    """Session with sane timeouts/retries for flaky supplier APIs."""
    s = requests.Session()
    retries = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST", "PUT", "PATCH", "DELETE"]),
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s


def _update_job_meta(**kw: Any) -> None:
    job = get_current_job()
    if job:
        job.meta = {**(job.meta or {}), **kw}
        job.save_meta()


def _persist_order_row(row: JSON) -> None:
    """Write a minimal record to DB if 'orders' table exists."""
    if not (db and inspect and text):
        return
    try:
        insp = inspect(db.engine)
        if not insp.has_table("orders"):
            return
        cols = insp.get_columns("orders")
        names = {c["name"] for c in cols}
        # Only insert what exists (works for a simple demo table)
        fields = {k: v for k, v in row.items() if k in names}
        if not fields:
            return
        placeholders = ", ".join(f":{k}" for k in fields.keys())
        columns = ", ".join(fields.keys())
        sql = text(f"INSERT INTO orders ({columns}) VALUES ({placeholders})")
        with db.engine.begin() as conn:
            conn.execute(sql, fields)
    except Exception as e:
        # Don't fail the job if logging is noisy—just stash it in job meta
        _update_job_meta(db_error=str(e))


# ------------------------
# Supplier registry
# ------------------------

@dataclass
class SupplierConfig:
    name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    # add fields as needed (auth type, headers, etc.)


def _supplier_demo(payload: JSON, cfg: SupplierConfig) -> Tuple[bool, JSON]:
    """
    Demo supplier: simulates latency and returns a fake PO number.
    """
    time.sleep(1.0)
    po = f"DEMO-{uuid.uuid4().hex[:8].upper()}"
    return True, {
        "purchase_order_id": po,
        "echo": payload,
    }


def _supplier_generic_rest(payload: JSON, cfg: SupplierConfig) -> Tuple[bool, JSON]:
    """
    Example of a JSON REST supplier. Customize per supplier.
    Expects env like:
      SUPPLIER_X_URL, SUPPLIER_X_API_KEY
    """
    assert cfg.base_url, "Supplier base_url missing"
    session = _requests_session()

    # map your payload ➜ supplier schema here
    outbound = {
        "sku": payload["sku"],
        "quantity": payload["qty"],
        "customer_ref": payload.get("customer_ref"),
    }

    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"

    # idempotency to prevent dup POs on retries
    idem = payload.get("idempotency_key") or uuid.uuid4().hex
    headers["Idempotency-Key"] = idem

    resp = session.post(
        f"{cfg.base_url.rstrip('/')}/orders",
        json=outbound,
        headers=headers,
        timeout=(5, 20),  # (connect, read)
    )

    try:
        body = resp.json()
    except Exception:
        body = {"text": resp.text}

    ok = 200 <= resp.status_code < 300
    result = {
        "status_code": resp.status_code,
        "response": body,
        "idempotency_key": idem,
    }
    return ok, result


# Supplier dispatcher. Add real suppliers here.
SUPPLIERS: Dict[str, Tuple[SupplierConfig, Callable[[JSON, SupplierConfig], Tuple[bool, JSON]]]] = {
    # Working demo stub:
    "demo": (SupplierConfig(name="demo"), _supplier_demo),

    # Example real supplier (uncomment & configure env):
    # "acme": (
    #     SupplierConfig(
    #         name="acme",
    #         base_url=os.getenv("SUPPLIER_ACME_URL"),
    #         api_key=os.getenv("SUPPLIER_ACME_API_KEY"),
    #     ),
    #     _supplier_generic_rest,
    # ),
}


# ------------------------
# Public job entrypoint
# ------------------------

def place_supplier_order(payload: JSON) -> JSON:
    """
    RQ job: place an order with the specified supplier.

    Expected payload:
      {
        "supplier_id": "demo",
        "sku": "ABC-123",
        "qty": 1,
        "customer_ref": "...",           # optional
        "idempotency_key": "...",        # optional (we can generate if absent)
      }
    """
    # ---- Validate input
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    supplier_id = str(payload.get("supplier_id", "")).strip().lower()
    sku = payload.get("sku")
    qty = payload.get("qty")

    if not supplier_id:
        raise ValueError("supplier_id is required")
    if not sku:
        raise ValueError("sku is required")
    try:
        qty_int = int(qty)
        if qty_int <= 0:
            raise ValueError
    except Exception:
        raise ValueError("qty must be a positive integer")

    _update_job_meta(stage="validated", supplier_id=supplier_id, sku=str(sku), qty=int(qty))

    # ---- Route to supplier handler
    if supplier_id not in SUPPLIERS:
        raise ValueError(f"unknown supplier_id '{supplier_id}'")

    cfg, handler = SUPPLIERS[supplier_id]
    ok, supplier_result = handler(payload, cfg)

    # ---- Optional persistence (best-effort)
    _persist_order_row({
        "id": str(uuid.uuid4()),
        "supplier_id": supplier_id,
        "sku": str(sku),
        "qty": int(qty),
        "status": "submitted" if ok else "failed",
        "result_json": str(supplier_result),  # store as TEXT; or use a JSON column if you have one
        "created_at": int(time.time()),
    })

    # ---- Final meta/result
    _update_job_meta(stage="completed", ok=ok)
    return {
        "ok": ok,
        "supplier": supplier_id,
        "result": supplier_result,
    }
