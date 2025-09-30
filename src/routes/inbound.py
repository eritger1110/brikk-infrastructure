# src/routes/inbound.py
# Only POST/OPTIONS on /order, plus simple GET/POST testers.
from __future__ import annotations

from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest

from src.services.queue import enqueue
from src.jobs.orders import place_supplier_order

# NOTE: only "/inbound" here; "/api" is added by main.py
inbound_bp = Blueprint("inbound", __name__, url_prefix="/inbound")

@inbound_bp.get("/ping")
def inbound_ping():
    return jsonify({"ok": True, "route": "/api/inbound/ping"}), 200

@inbound_bp.post("/echo")
def inbound_echo():
    data = request.get_json(silent=True) or {}
    return jsonify({"ok": True, "echo": data}), 200

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
