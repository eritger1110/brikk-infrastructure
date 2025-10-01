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
    # Sanity check that the blueprint is live
    return jsonify({"ok": True, "bp": "inbound"}), 200


@inbound_bp.route("/order", methods=["POST", "OPTIONS"])
def inbound_order():
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


# ----------------------------
# TEMP: job status inspector
# ----------------------------
@inbound_bp.get("/status/<job_id>")
def inbound_job_status(job_id: str):
    """
    Inspect an RQ job by id. Handy to verify the worker is pulling and finishing jobs.
    Return shape is safe to log and debug with; remove this route later.
    """
    try:
        from src.services.queue import _redis  # same connection used by the queue
        from rq.job import Job

        job: Optional[Job] = Job.fetch(job_id, connection=_redis)  # type: ignore
    except Exception:
        return jsonify({"error": "job_not_found", "job_id": job_id}), 404

    def _iso(dt: Optional[datetime]) -> Optional[str]:
        try:
            return dt.isoformat() if dt else None
        except Exception:
            return None

    info = {
        "id": job.id,
        "status": job.get_status(),
        "enqueued_at": _iso(getattr(job, "enqueued_at", None)),
        "started_at": _iso(getattr(job, "started_at", None)),
        "ended_at": _iso(getattr(job, "ended_at", None)),
        "meta": getattr(job, "meta", {}) or {},
        # Only include result if finished (avoid huge payloads/errors mid-run)
        "result": job.result if job.is_finished else None,
        "exc_info": job.exc_info,  # stack if failed
    }
    return jsonify(info), 200
