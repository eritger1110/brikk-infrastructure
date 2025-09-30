# src/routes/inbound.py
from __future__ import annotations

from typing import Any, Dict
from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

# Only the sub-path here; /api is added in main.py when the blueprint is registered
inbound_bp = Blueprint("inbound", __name__, url_prefix="/inbound")


@inbound_bp.get("/_ping")
def inbound_ping():
    # If this returns 200, the blueprint is definitely registered
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
            def place_supplier_order(data: Dict[str, Any]) -> Dict[str, Any]:
                return {"echo": data}

        job = enqueue(place_supplier_order, payload)
        job_id = getattr(job, "id", None)
        return jsonify({"queued": True, "job_id": job_id}), 202

    except Exception as e:
        current_app.logger.exception("[inbound] enqueue failed")
        return jsonify({"queued": False, "error": str(e)}), 500
