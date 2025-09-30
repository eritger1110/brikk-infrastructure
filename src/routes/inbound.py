# src/routes/inbound.py
from __future__ import annotations

from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest

from src.services.queue import enqueue
from src.jobs.orders import place_supplier_order

# IMPORTANT: only the sub-path here; /api is added in main.py
inbound_bp = Blueprint("inbound", __name__, url_prefix="/inbound")


@inbound_bp.route("/order", methods=["POST", "OPTIONS"])
def inbound_order():
    # CORS preflight
    if request.method == "OPTIONS":
        return ("", 204)

    # Accept JSON object only
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        raise BadRequest("JSON body must be an object")

    # Queue the background job
    job = enqueue(place_supplier_order, payload)

    # RQ returns a Job; be resilient in case enqueue stub changes
    job_id = getattr(job, "id", None)

    # 202 = accepted for async processing
    return jsonify({"queued": True, "job_id": job_id}), 202
