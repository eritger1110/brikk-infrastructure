
"""
AI Coordination Routes

Provides API endpoints for AI-powered coordination optimization and intelligent routing.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from src.services.ai_coordination_service import AICoordinationService
from src.database import db

ai_coordination_bp = Blueprint("ai_coordination_bp", __name__)
ai_coordination_service = AICoordinationService(db)

@ai_coordination_bp.route("/api/v1/ai/route", methods=["POST"])
@jwt_required()
def intelligent_route():
    """
    Intelligently routes a workflow to the most appropriate agent.
    """
    data = request.get_json()
    workflow_id = data.get("workflow_id")
    initial_data = data.get("initial_data")

    if not workflow_id or not initial_data:
        return jsonify({"error": "workflow_id and initial_data are required"}), 400

    try:
        result = ai_coordination_service.intelligent_route(workflow_id, initial_data)
        return jsonify(result), 200
    except (ValueError, RuntimeError) as e:
        return jsonify({"error": str(e)}), 404

@ai_coordination_bp.route("/api/v1/ai/optimize", methods=["POST"])
@jwt_required()
def optimize_coordination_strategy():
    """
    Optimizes the coordination strategy for a given workflow.
    """
    data = request.get_json()
    workflow_id = data.get("workflow_id")

    if not workflow_id:
        return jsonify({"error": "workflow_id is required"}), 400

    try:
        result = ai_coordination_service.optimize_coordination_strategy(workflow_id)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

