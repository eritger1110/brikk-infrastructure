# -*- coding: utf-8 -*-
"""
Workflows Route

Provides API endpoints for managing multi-step coordination workflows.
"""

from flask import Blueprint, request, jsonify
from src.services.workflow_service import WorkflowService
from flask_jwt_extended import jwt_required, get_jwt
from src.database import db

workflows_bp = Blueprint("workflows", __name__)


@workflows_bp.route("/api/v1/workflows", methods=["POST"])
@jwt_required()
def create_workflow():
    data = request.get_json()
    claims = get_jwt()
    organization_id = claims.get("organization_id")
    print(
        f"Creating workflow with name: {data.get('name')}, org_id: {organization_id}")
    db_session = db.session
    workflow_service = WorkflowService(db_session)
    workflow = workflow_service.create_workflow(
        name=data["name"],
        description=data.get("description"),
        organization_id=organization_id
    )
    return jsonify({"id": workflow.id, "name": workflow.name}), 201


@workflows_bp.route("/api/v1/workflows/<int:workflow_id>", methods=["GET"])
@jwt_required()
def get_workflow(workflow_id):
    claims = get_jwt()
    organization_id = claims.get("organization_id")
    db_session = db.session
    workflow_service = WorkflowService(db_session)
    workflow = workflow_service.get_workflow(workflow_id)
    if not workflow or workflow.organization_id != organization_id:
        return jsonify({"error": "Workflow not found"}), 404
    return jsonify({"id": workflow.id, "name": workflow.name,
                   "description": workflow.description})


@workflows_bp.route("/api/v1/workflows/<int:workflow_id>/steps",
                    methods=["POST"])
@jwt_required()
def create_workflow_step(workflow_id):
    data = request.get_json()
    claims = get_jwt()
    organization_id = claims.get("organization_id")
    db_session = db.session
    workflow_service = WorkflowService(db_session)
    workflow = workflow_service.get_workflow(workflow_id)
    if not workflow or workflow.organization_id != organization_id:
        return jsonify({"error": "Workflow not found"}), 404

    workflow_step = workflow_service.create_workflow_step(
        workflow_id=workflow_id,
        name=data["name"],
        description=data.get("description"),
        agent_id=data["agent_id"],
        action=data["action"],
        params=data.get("params"),
        order=data["order"]
    )
    return jsonify({"id": workflow_step.id, "name": workflow_step.name}), 201


@workflows_bp.route("/api/v1/workflows/<int:workflow_id>/execute",
                    methods=["POST"])
@jwt_required()
def execute_workflow(workflow_id):
    data = request.get_json()
    claims = get_jwt()
    organization_id = claims.get("organization_id")
    db_session = db.session
    workflow_service = WorkflowService(db_session)
    workflow = workflow_service.get_workflow(workflow_id)
    if not workflow or workflow.organization_id != organization_id:
        return jsonify({"error": "Workflow not found"}), 404

    workflow_execution = workflow_service.execute_workflow(
        workflow_id=workflow_id,
        context=data.get("context")
    )
    return jsonify({"id": workflow_execution.id,
                   "status": workflow_execution.status}), 202
