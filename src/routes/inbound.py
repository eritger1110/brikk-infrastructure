# -*- coding: utf-8 -*-
# src/routes/inbound.py
from __future__ import annotations

import hmac
import os
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

# Only the sub-path here; /api is added in main.py when the blueprint is
# registered
inbound_bp = Blueprint("inbound", __name__, url_prefix="/inbound")


# ---------- Signature verification helpers ----------

def _parse_sig_header(header_val: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Parse "X-Brikk-Signature: t=<unix>,v1=<hex>" -> (timestamp, hex)
    Returns (None, None) if the format is invalid.
    """
    try:
        parts = [p.strip() for p in header_val.split(",")]
        kv = dict(p.split("=", 1) for p in parts if "=" in p)
        ts = int(kv.get("t", ""))
        v1 = kv.get("v1", "")
        if not v1 or any(c not in "0123456789abcdef" for c in v1.lower()):
            return None, None
        return ts, v1
    except Exception:
        return None, None


def _verify_signature(body_bytes: bytes) -> Tuple[bool, int, str]:
    """
    Verify the request signature if INBOUND_REQUIRE_SIGNATURE=1.
    Returns (ok, http_status, message).
    """
    require = os.getenv("INBOUND_REQUIRE_SIGNATURE", "0") == "1"
    if not require:
        return True, 200, "signature not required"

    secret = os.getenv("INBOUND_SIGNING_SECRET") or ""
    if not secret:
        current_app.logger.error(
            "INBOUND_REQUIRE_SIGNATURE=1 but INBOUND_SIGNING_SECRET is missing")
        return False, 500, "server_signature_not_configured"

    sig_hdr = request.headers.get("X-Brikk-Signature", "")
    ts, v1_hex = _parse_sig_header(sig_hdr)
    if ts is None or v1_hex is None:
        return False, 401, "bad_signature_header"

    # Check clock skew
    max_skew = int(os.getenv("INBOUND_MAX_SKEW", "300"))
    now = int(datetime.now(tz=timezone.utc).timestamp())
    if abs(now - ts) > max_skew:
        return False, 401, "timestamp_out_of_range"

    # Compute expected HMAC
    msg = f"{ts}.".encode("utf-8") + body_bytes
    expected = hmac.new(secret.encode("utf-8"), msg, sha256).hexdigest()

    if not hmac.compare_digest(expected, v1_hex):
        return False, 401, "signature_mismatch"

    return True, 200, "ok"


# ---------- Routes ----------

@inbound_bp.get("/_ping")
def inbound_ping():
    """Sanity check that the blueprint is live."""
    return jsonify({"ok": True, "bp": "inbound"}), 200


@inbound_bp.route("/order", methods=["POST", "OPTIONS"])
def inbound_order():
    """
    Enqueue a supplier order job.

    POST JSON body (object), e.g.:
      { "supplier_id": "demo", "sku": "ABC-123", "qty": 1 }
    """
    # CORS preflight short-circuit
    if request.method == "OPTIONS":
        return ("", 204)

    # Use raw bytes so the client and server sign the exact same content
    raw = request.get_data(cache=True, as_text=False) or b"{}"

    # Verify signature if required
    ok, code, msg = _verify_signature(raw)
    if not ok:
        return jsonify({"queued": False, "error": msg}), code

    # Parse JSON
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        raise BadRequest("JSON body must be an object")

    # Lazy import so missing jobs/queue modules don't prevent the BP from
    # registering
    try:
        from src.services.queue import enqueue  # rq wrapper
        try:
            from src.jobs.orders import place_supplier_order  # your real job
        except Exception as e:
            current_app.logger.warning(
                f"[inbound] couldn't import place_supplier_order, using echo fallback: {e}"
            )

            # fallback job that just echoes the payload (so enqueue still
            # works)
            # type: ignore[no-redef]
            def place_supplier_order(data: Dict[str, Any]) -> Dict[str, Any]:
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
        return jsonify(
            {"error": "job_not_found_in_redis", "job_id": job_id}), 404
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
