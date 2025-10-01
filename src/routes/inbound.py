# src/routes/inbound.py
from __future__ import annotations

from typing import Any, Dict
from flask import Blueprint, request, jsonify, current_app

# No url_prefix here — we’ll attach it in main.py as /api/inbound
inbound_bp = Blueprint("inbound", __name__)

@inbound_bp.get("/_ping")
def inbound_ping():
    return jsonify({"ok": True, "bp": "inbound"}), 200

@inbound_bp.route("/order", methods=["POST", "OPTIONS"])
def inbound_order():
    # CORS preflight short-circuit
    if request.method == "OPTIONS":
        return ("", 204)

    payload: Dict[str, Any] = request.get_json(silent=True) or {}

    # Try the real job; fall back to echo so the route still works
    try:
        from src.services.queue import enqueue
        try:
            from src.jobs.orders import place_supplier_order
        except Exception as e:
            current_app.logger.warning(
                f"[inbound] place_supplier_order import failed, using echo: {e}"
            )
            def place_supplier_order(data: Dict[str, Any]) -> Dict[str, Any]:
                return {"echo": data}

        job = enqueue(place_supplier_order, payload)
        return jsonify({"queued": True, "job_id": getattr(job, "id", None)}), 202

    except Exception as e:
        current_app.logger.exception("[inbound] enqueue failed")
        return jsonify({"queued": False, "error": str(e)}), 500
