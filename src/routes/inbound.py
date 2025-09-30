# src/routes/inbound.py
from __future__ import annotations

from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest

# Import inside the function is fine, but keeping at top is clearer.
from src.services.queue import enqueue
from src.jobs.orders import place_supplier_order

# IMPORTANT: only the sub-path here; /api is added in main.py
inbound_bp = Blueprint("inbound", __name__, url_prefix="/inbound")

@inbound_bp.get("/ping")
def inbound_ping():
    # simple GET route to prove the blueprint is mounted
    return jsonify({"ok": True, "where": "inbound"}), 200

@inbound_bp.route("/order", methods=["POST", "OPTIONS"])
def inbound_order():
    # CORS preflight
    if request.method == "OPTIONS":
        return ("", 204)

    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        raise BadRequest("JSON body must be an object")

    job = enqueue(place_supplier_order, payload)
    job_id = getattr(job, "id", None)
    # 202: accepted for async processing
    return jsonify({"queued": True, "job_id": job_id}), 202
