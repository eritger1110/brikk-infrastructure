# src/routes/coordination.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from src.models.agent import Agent, Coordination, db
from datetime import datetime, timezone
import time
import random

coordination_bp = Blueprint("coordination_bp", __name__)

@coordination_bp.post("/api/coordination/run")
@jwt_required()
def run():
    """
    Simple user-facing orchestration endpoint.
    Replace the body of this function with your real pipeline/orchestrator call.
    """
    claims = get_jwt()
    email = claims.get("email")

    data = request.get_json() or {}
    prompt = data.get("prompt", "")

    # --- DEMO implementation (replace with real logic) ---
    start = time.time()
    time.sleep(0.15)  # pretend work
    output = f"[Brikk demo] User={email} Prompt={prompt!r} -> processed"
    duration_ms = round((time.time() - start) * 1000, 2)

    return jsonify({
        "ok": True,
        "output": output,
        "latency_ms": duration_ms
    })


@coordination_bp.get("/api/metrics")
@jwt_required()
def metrics():
    """
    Minimal metrics for the dashboard graphs.
    Replace with your real metrics collection if available.
    """
    total_agents   = Agent.query.count()
    active_agents  = Agent.query.filter_by(status='active').count()

    # Fake “today” numbers if you haven’t populated Coordination yet
    total_coord = Coordination.query.count()
    completed   = Coordination.query.filter_by(status="completed").count()
    success_rate = round((completed / max(total_coord, 1)) * 100, 2)

    # Some sample series (client will chart these)
    series = {
        "last10m": [random.randint(1, 8) for _ in range(10)],
        "latency": [random.randint(80, 220) for _ in range(10)],
    }

    return jsonify({
        "active_agents": active_agents,
        "total_agents": total_agents,
        "total_coordinations": total_coord,
        "success_rate": success_rate,
        "series": series,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
