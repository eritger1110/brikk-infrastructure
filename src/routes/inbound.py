# src/routes/inbound.py
from __future__ import annotations

import hmac
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

inbound_bp = Blueprint("inbound", __name__, url_prefix="/inbound")


# ---------------------------
# Helpers: signatures & utils
# ---------------------------

def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v is not None and v != "" else default


def _parse_signature_header(header_val: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Parse: X-Brikk-Signature: t=<ts>,v1=<hex>
    Returns (ts, v1) where ts is int or None.
    """
    try:
        parts = dict(item.split("=", 1) for item in header_val.split(","))
        ts = int(parts.get("t", "")) if "t" in parts else None
        v1 = parts.get("v1")
        return ts, v1
    except Exception:
        return None, None


def _constant_time_equal(a: str, b: str) -> bool:
    try:
        return hmac.compare_digest(a, b)
    except Exception:
        return False


def _compute_v1(secret: str, ts: int, body_bytes: bytes) -> str:
    mac = hmac.new(secret.encode("utf-8"), f"{ts}.".encode("utf-8") + body_bytes, "sha256")
    return mac.hexdigest()


def _verify_signature_or_401(req) -> Optional[Tuple[int, Any]]:
    """
    If REQUIRE_INBOUND_SIGNATURE=1, verify header. On failure, return (status, json).
    If verification passes or not required, return None.
    """
    require = _get_env("REQUIRE_INBOUND_SIGNATURE", "1") == "1"
    if not require:
        return None

    secret = _get_env("INBOUND_SIGNING_SECRET")
    secret_alt = _get_env("INBOUND_SIGNING_SECRET_ALT")
    if not secret:
        return  (500, {"error": "signing_not_configured"})

    header_val = req.headers.get("X-Brikk-Signature")
    if not header_val:
        return (401, {"error": "missing_signature_header"})

    ts, v1 = _parse_signature_header(header_val)
    if ts is None or not v1:
        return (401, {"error": "malformed_signature_header"})

    # Clock skew
    max_skew = int(_get_env("INBOUND_MAX_SKEW", "300") or "300")
    now = int(time.time())
    if abs(now - ts) > max_skew:
        return (401, {"error": "timestamp_out_of_range", "now": now, "ts": ts, "max_skew": max_skew})

    body_bytes = req.get_data() or b""
    expected = _compute_v1(secret, ts, body_bytes)
    if _constant_time_equal(expected, v1):
        return None

    # Allow rotation with alternate secret
    if secret_alt:
        expected_alt = _compute_v1(secret_alt, ts, body_bytes)
        if _constant_time_equal(expected_alt, v1):
            return None

    return (401, {"error": "bad_signature"})


def _iso(dt: Optional[datetime]) -> Optional[str]:
    try:
        return dt.isoformat() if dt else None
    except Exception:
        return None


# ---------------------------
# Routes
# ---------------------------

@inbound_bp.get("/_ping")
def inbound_ping():
    return jsonify({"ok": True, "bp": "inbound"}), 200


@inbound_bp.route("/order", methods=["POST", "OPTIONS"])
def inbound_order():
    if request.method == "OPTIONS":
        return ("", 204)

    # Signature check (optional/controlled by env)
    sig_err = _verify_signature_or_401(request)
    if sig_err is not None:
        code, payload = sig_err
        return jsonify(payload), code

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        raise BadRequest("JSON body must be an object")

    try:
        from src.services.queue import enqueue  # rq wrapper
        try:
            from src.jobs.orders import place_supplier_order  # your job
        except Exception as e:
            current_app.logger.warning(
                f"[inbound] couldn't import place_supplier_order, using echo fallback: {e}"
            )
            def place_supplier_order(data: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[no-redef]
                return {"echo": data}

        job = enqueue(place_supplier_order, payload)
        return jsonify({"queued": True, "job_id": getattr(job, "id", None)}), 202

    except Exception as e:
        current_app.logger.exception("[inbound] enqueue failed")
        return jsonify({"queued": False, "error": str(e)}), 500


@inbound_bp.get("/status/<job_id>")
def inbound_job_status(job_id: str):
    from rq.job import Job
    from rq.exceptions import NoSuchJobError
    try:
        from src.services.queue import _redis
        job: Job = Job.fetch(job_id, connection=_redis)
    except NoSuchJobError:
        return jsonify({"error": "job_not_found_in_redis", "job_id": job_id}), 404
    except Exception as e:
        return jsonify({"error": "redis_error", "detail": str(e)}), 500

    info = {
        "id": job.id,
        "status": job.get_status(),
        "enqueued_at": _iso(getattr(job, "enqueued_at", None)),
        "started_at": _iso(getattr(job, "started_at", None)),
        "ended_at": _iso(getattr(job, "ended_at", None)),
        "meta": getattr(job, "meta", {}) or {},
        "result": job.result if job.is_finished else None,
        "exc_info": job.exc_info,
    }
    return jsonify(info), 200


@inbound_bp.get("/_redis_info")
def inbound_redis_info():
    """Quick visibility into which Redis the web is using."""
    try:
        from src.services.queue import _redis, REDIS_URL, queue
        pong = _redis.ping()
        info = _redis.connection_pool.connection_kwargs.copy()
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


@inbound_bp.get("/_queue_depth")
def inbound_queue_depth():
    """Small inspector to see how many jobs are waiting."""
    try:
        from rq import Queue
        from src.services.queue import _redis, queue as default_queue
        q = Queue(default_queue.name, connection=_redis)
        return jsonify({"queue": q.name, "count": q.count}), 200
    except Exception as e:
        return jsonify({"error": "queue_depth_error", "detail": str(e)}), 500
