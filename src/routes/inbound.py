# src/routes/inbound.py
from __future__ import annotations

import hmac
import os
from hashlib import sha256
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

# Only the sub-path here; /api is added in main.py when the blueprint is registered
inbound_bp = Blueprint("inbound", __name__, url_prefix="/inbound")


def _cfg(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Read config from Flask app.config first, then environment, then default.
    This lets main.py inject values while still working if module is imported standalone.
    """
    try:
        v = current_app.config.get(name)  # type: ignore[attr-defined]
        if v is not None:
            return str(v)
    except Exception:
        pass
    return os.getenv(name, default)


def _parse_sig_header(header: str) -> Tuple[Optional[int], Optional[str]]:
    """
    X-Brikk-Signature: 't=<unix_ts>,v1=<hex>'
    Returns (ts, v1) or (None, None) if invalid.
    """
    if not header:
        return None, None
    parts = dict(
        kv.split("=", 1) for kv in (p.strip() for p in header.split(",")) if "=" in kv
    )
    try:
        ts = int(parts.get("t", ""))
        v1 = parts.get("v1")
        return ts, v1
    except Exception:
        return None, None


def _verify_signature(raw_body: bytes) -> Tuple[bool, str]:
    """
    Verify HMAC SHA256 over message: f"{ts}." + raw_body
    - secret: INBOUND_SIGNING_SECRET
    - skew: INBOUND_MAX_SKEW (seconds)
    Returns (ok, error_message)
    """
    required = _cfg("REQUIRE_INBOUND_SIGNATURE", "1") == "1"
    secret = _cfg("INBOUND_SIGNING_SECRET")
    header = request.headers.get("X-Brikk-Signature", "")

    if not required:
        return True, ""

    if not secret:
        return False, "signing_secret_missing"

    ts, v1 = _parse_sig_header(header)
    if ts is None or v1 is None:
        return False, "invalid_signature_header"

    # Clock skew window
    max_skew = int(_cfg("INBOUND_MAX_SKEW", "300") or "300")
    now = int(datetime.now(timezone.utc).timestamp())
    if abs(now - ts) > max_skew:
        return False, "timestamp_out_of_window"

    msg = f"{ts}.".encode("utf-8") + raw_body
    expected = hmac.new(secret.encode("utf-8"), msg, sha256).hexdigest()

    if not hmac.compare_digest(expected, v1):
        return False, "signature_mismatch"

    return True, ""


@inbound_bp.get("/_ping")
def inbound_ping():
    """Sanity check that the blueprint is live."""
    return jsonify({"ok": True, "bp": "inbound"}), 200


@inbound_bp.route("/order", methods=["POST", "OPTIONS"])
def inbound_order():
    """Enqueue a supplier order job.

    POST JSON body (object), e.g.:
      { "supplier_id": "demo", "sku": "ABC-123", "qty": 1 }
    """
    # CORS preflight short-circuit
    if request.method == "OPTIONS":
        return ("", 204)

    # Use the raw body for signature verification
    raw = request.get_data(cache=True, as_text=False)  # cache=True so get_json still works
    ok, err = _verify_signature(raw)
    if not ok:
        return jsonify({"ok": False, "error": err}), 401

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        raise BadRequest("JSON body must be an object")

    # Lazy import so a missing jobs module doesn't prevent the BP from registering
    try:
        from src.services.queue import enqueue  # rq wrapper
        try:
            from src.jobs.orders import place_supplier_order  # your real job
        except Exception as e:
            current_app.logger.warning(
                f"[inbound] couldn't import place_supplier_order, using echo fallback: {e}"
            )

            # fallback job that just echoes the payload (so enqueue still works)
            def place_supplier_order(data: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[no-redef]
                return {"echo": data}

        job = enqueue(place_supplier_order, payload)
        job_id = getattr(job, "id", None)
        return jsonify({"queued": True, "job_id": job_id}), 202

    except Exception as e:
        current_app.logger.exception("[inbound] enqueue failed")
        return jsonify({"queued": False, "error": str(e)}), 500


@inbound_bp.get("/status/<job_id>")
def inbound_job_status(job_id: str):
    """Inspect an RQ job by id. Handy to verify the worker is pulling/finishing jobs."""
    from rq.job import Job
    from rq.exceptions import NoSuchJobError
    try:
        from src.services.queue import _redis  # use same connection as the queue
        job: Job = Job.fetch(job_id, connection=_redis)
    except NoSuchJobError:
        return jsonify({"error": "job_not_found_in_redis", "job_id": job_id}), 404
    except Exception as e:
        return jsonify({"error": "redis_error", "detail": str(e)}), 500

    def _iso(dt: Optional[datetime]) -> Optional[str]:
        try:
            return dt.isoformat() if dt else None
        except Exception:
            return None

    return jsonify({
        "id": job.id,
        "status": job.get_status(),
        "enqueued_at": _iso(getattr(job, "enqueued_at", None)),
        "started_at": _iso(getattr(job, "started_at", None)),
        "ended_at": _iso(getattr(job, "ended_at", None)),
        "meta": getattr(job, "meta", {}) or {},
        # Only include result if finished (avoid huge payloads/errors mid-run)
        "result": job.result if job.is_finished else None,
        "exc_info": job.exc_info,  # stack if failed
    }), 200


@inbound_bp.get("/_redis_info")
def inbound_redis_info():
    """Quick visibility into which Redis the web is using."""
    try:
        from src.services.queue import _redis, REDIS_URL, queue
        pong = _redis.ping()
        info = _redis.connection_pool.connection_kwargs.copy()
        # Strip password if present
        if "password" in info:
            info["password"] = "***"
        return jsonify({
            "redis_url_env": REDIS_URL,
            "connection": info,
            "queue_name": queue.name,
            "ping": pong,
        }), 200
    except Exception as e:
        return jsonify({"error": "redis_info_error", "detail": str(e)}), 500
