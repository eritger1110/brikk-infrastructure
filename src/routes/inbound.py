# src/routes/inbound.py
from flask import Blueprint, request, jsonify
from src.services.queue import enqueue
from src.jobs.orders import place_supplier_order

inbound_bp = Blueprint("inbound", __name__, url_prefix="/api/inbound")

@inbound_bp.post("/order")
def inbound_order():
    payload = request.get_json(silent=True) or {}
    job = enqueue(place_supplier_order, payload)
    return jsonify({"queued": True, "job_id": job.id})
