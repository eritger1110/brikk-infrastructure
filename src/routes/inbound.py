# src/routes/inbound.py
from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime

from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

# Only the sub-path here; /api is added in main.py when the blueprint is registered
inbound_bp = Blueprint("inbound", __name__, url_prefix="/inbound")


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
