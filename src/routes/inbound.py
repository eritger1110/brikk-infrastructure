# src/routes/inbound.py
from __future__ import annotations

from typing import Any, Dict
from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

# NOTE: only the sub-path here; /api is added in main.py
inbound_bp = Blueprint("inbound", __name__, url_prefix="/inbound")


# Explicitly list GET/HEAD/OPTIONS so Flask can’t misinterpret methods
@inbound_bp.route("/_ping", methods=["GET", "HEAD", "OPTIONS"])
def inbound_ping():
    if request.method == "OPTIONS":
        # Fast CORS preflight response
        return ("", 204)
    current_app.logger.info("[inbound] /_ping hit with method %s", request.method)
    return jsonify({"ok": True, "bp": "inbound"}), 200


# Explicitly list POST/OPTIONS and short-circuit preflight
@inbound_bp.route("/order", methods=["POST", "OPTIONS"])
def inbound_order():
    if request.method == "OPTIONS":
        return ("", 204)

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        raise BadRequest("JSON body must be an object")

    try:
        from src.services.queue import enqueue
        try:
            from src.jobs.orders import place_supplier_order
        except Exception as e:
            current_app.logger.warning(
                "[inbound] place_supplier_order import failed; using echo. %s", e
            )

            def place_supplier_order(data: Dict[str, Any]) -> Dict[str, Any]:
                return {"echo": data}

        job = enqueue(place_supplier_order, payload)
        job_id = getattr(job, "id", None)
        current_app.logger.info("[inbound] queued job %s", job_id)
        return jsonify({"queued": True, "job_id": job_id}), 202

    except Exception as e:
        current_app.logger.exception("[inbound] enqueue failed")
        return jsonify({"queued": False, "error": str(e)}), 500
