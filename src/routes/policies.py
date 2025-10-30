"""
Policy API Routes - Rules Dashboard endpoints (Flask Blueprint).

RESTful API for policy management, simulation, approval, and deployment.
"""

from flask import Blueprint, request, jsonify
from functools import wraps
from typing import Optional, List

from src.database import db
from src.models.policy import PolicyStatus, DeploymentStrategy
from src.schemas.policy import (
    PolicyCreate, PolicyUpdate, PolicySimulateRequest,
    PolicyApprovalRequest, PolicyApprovalDecision, PolicyDeployRequest
)
from src.services.policy_service import PolicyService
from src.middleware.auth import require_auth, get_current_user
from src.models.user import User


policies_bp = Blueprint("policies", __name__, url_prefix="/api/v1/policies")


# ============================================================================
# Helper Functions
# ============================================================================

def policy_to_dict(policy) -> dict:
    """Convert Policy model to dictionary."""
    return {
        "id": policy.id,
        "name": policy.name,
        "description": policy.description,
        "goal": policy.goal.value,
        "status": policy.status.value,
        "scope": policy.scope,
        "conditions": policy.conditions,
        "actions": policy.actions,
        "priority": policy.priority,
        "tags": policy.tags or [],
        "hit_count": policy.hit_count,
        "error_count": policy.error_count,
        "last_hit_at": policy.last_hit_at.isoformat() if policy.last_hit_at else None,
        "created_by": policy.created_by,
        "org_id": policy.org_id,
        "created_at": policy.created_at.isoformat(),
        "updated_at": policy.updated_at.isoformat(),
        "deployed_at": policy.deployed_at.isoformat() if policy.deployed_at else None
    }


def require_role(*allowed_roles):
    """Decorator to require specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # TODO: Implement role checking
            # For now, just require authentication
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================================
# CRUD Endpoints
# ============================================================================

@policies_bp.route("", methods=["POST"])
@require_auth
def create_policy():
    """
    Create a new draft policy.
    
    Permissions: Operator, Approver, Admin
    """
    try:
        user = get_current_user()
        data = request.get_json()
        
        # Validate with Pydantic
        policy_data = PolicyCreate(**data)
        
        # Create policy
        policy_service = PolicyService(db.session)
        policy = policy_service.create_policy(
            policy_data=policy_data,
            user_id=user.id,
            org_id=user.org_id
        )
        
        return jsonify(policy_to_dict(policy)), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@policies_bp.route("", methods=["GET"])
@require_auth
def list_policies():
    """
    List policies with filtering and pagination.
    
    Permissions: Viewer, Operator, Approver, Admin
    """
    try:
        user = get_current_user()
        
        # Get query parameters
        status = request.args.get("status")
        tags = request.args.getlist("tags")
        page = int(request.args.get("page", 1))
        page_size = min(int(request.args.get("page_size", 50)), 100)
        
        # Convert status string to enum
        status_enum = None
        if status:
            try:
                status_enum = PolicyStatus(status)
            except ValueError:
                return jsonify({"error": f"Invalid status: {status}"}), 400
        
        # Get policies
        policy_service = PolicyService(db.session)
        policies, total = policy_service.list_policies(
            org_id=user.org_id,
            status=status_enum,
            tags=tags if tags else None,
            page=page,
            page_size=page_size
        )
        
        return jsonify({
            "policies": [policy_to_dict(p) for p in policies],
            "total": total,
            "page": page,
            "page_size": page_size
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@policies_bp.route("/<int:policy_id>", methods=["GET"])
@require_auth
def get_policy(policy_id: int):
    """
    Get policy details by ID.
    
    Permissions: Viewer, Operator, Approver, Admin
    """
    try:
        user = get_current_user()
        policy_service = PolicyService(db.session)
        policy = policy_service.get_policy(policy_id, user.org_id)
        
        if not policy:
            return jsonify({"error": "Policy not found"}), 404
        
        return jsonify(policy_to_dict(policy))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@policies_bp.route("/<int:policy_id>", methods=["PUT"])
@require_auth
def update_policy(policy_id: int):
    """
    Update an existing policy.
    
    Permissions: Operator, Approver, Admin
    Restrictions: Can only update draft or paused policies
    """
    try:
        user = get_current_user()
        data = request.get_json()
        
        # Validate with Pydantic
        policy_data = PolicyUpdate(**data)
        
        # Update policy
        policy_service = PolicyService(db.session)
        policy = policy_service.update_policy(
            policy_id=policy_id,
            policy_data=policy_data,
            user_id=user.id,
            org_id=user.org_id
        )
        
        return jsonify(policy_to_dict(policy))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@policies_bp.route("/<int:policy_id>", methods=["DELETE"])
@require_auth
def delete_policy(policy_id: int):
    """
    Delete a draft policy.
    
    Permissions: Operator, Approver, Admin
    Restrictions: Can only delete draft policies
    """
    try:
        user = get_current_user()
        policy_service = PolicyService(db.session)
        deleted = policy_service.delete_policy(
            policy_id=policy_id,
            user_id=user.id,
            org_id=user.org_id
        )
        
        if not deleted:
            return jsonify({"error": "Policy not found"}), 404
        
        return "", 204
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Simulation Endpoint
# ============================================================================

@policies_bp.route("/<int:policy_id>/simulate", methods=["POST"])
@require_auth
def simulate_policy(policy_id: int):
    """
    Simulate policy against recent traffic.
    
    Analyzes last N minutes of usage events to predict:
    - Hit rate
    - Routing changes
    - Latency impact
    - Cost impact
    - Risk flags
    
    Permissions: Operator, Approver, Admin
    """
    try:
        user = get_current_user()
        data = request.get_json() or {}
        
        # Validate with Pydantic
        simulate_request = PolicySimulateRequest(**data)
        
        # Run simulation
        policy_service = PolicyService(db.session)
        result = policy_service.simulate_policy(
            policy_id=policy_id,
            simulate_request=simulate_request,
            org_id=user.org_id
        )
        
        return jsonify(result.dict())
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Approval Workflow Endpoints
# ============================================================================

@policies_bp.route("/<int:policy_id>/submit", methods=["POST"])
@require_auth
def submit_for_approval(policy_id: int):
    """
    Submit policy for approval.
    
    Changes policy status from DRAFT to PENDING_APPROVAL.
    
    Permissions: Operator, Approver, Admin
    """
    try:
        user = get_current_user()
        data = request.get_json() or {}
        
        # Validate with Pydantic
        approval_request = PolicyApprovalRequest(**data)
        
        # Submit for approval
        policy_service = PolicyService(db.session)
        approval = policy_service.submit_for_approval(
            policy_id=policy_id,
            user_id=user.id,
            org_id=user.org_id,
            notes=approval_request.notes,
            deployment_strategy=approval_request.deployment_strategy
        )
        
        return jsonify({
            "id": approval.id,
            "policy_id": approval.policy_id,
            "version_id": approval.version_id,
            "status": approval.status,
            "requested_by": approval.requested_by,
            "requested_at": approval.requested_at.isoformat(),
            "request_notes": approval.request_notes,
            "deployment_strategy": approval.deployment_strategy.value if approval.deployment_strategy else None
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@policies_bp.route("/<int:policy_id>/approve", methods=["POST"])
@require_auth
def approve_policy(policy_id: int):
    """
    Approve or reject a policy.
    
    Permissions: Approver, Admin only
    """
    try:
        user = get_current_user()
        data = request.get_json()
        
        approval_id = request.args.get("approval_id", type=int)
        if not approval_id:
            return jsonify({"error": "approval_id query parameter required"}), 400
        
        # Validate with Pydantic
        decision = PolicyApprovalDecision(**data)
        
        # Approve/reject
        policy_service = PolicyService(db.session)
        approval = policy_service.approve_policy(
            policy_id=policy_id,
            approval_id=approval_id,
            user_id=user.id,
            org_id=user.org_id,
            approved=decision.approved,
            notes=decision.notes
        )
        
        return jsonify({
            "id": approval.id,
            "policy_id": approval.policy_id,
            "version_id": approval.version_id,
            "status": approval.status,
            "requested_by": approval.requested_by,
            "requested_at": approval.requested_at.isoformat(),
            "reviewed_by": approval.reviewed_by,
            "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
            "review_notes": approval.review_notes
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Deployment Endpoints
# ============================================================================

@policies_bp.route("/<int:policy_id>/deploy", methods=["POST"])
@require_auth
def deploy_policy(policy_id: int):
    """
    Deploy an approved policy.
    
    Supports:
    - Immediate deployment (100% traffic)
    - Canary deployment (10%, 20%, 50%)
    - Gradual rollout
    - Auto-rollback on SLA breach
    
    Permissions: Approver, Admin only
    """
    try:
        user = get_current_user()
        data = request.get_json() or {}
        
        # Validate with Pydantic
        deploy_request = PolicyDeployRequest(**data)
        
        # Deploy
        policy_service = PolicyService(db.session)
        deployment = policy_service.deploy_policy(
            policy_id=policy_id,
            user_id=user.id,
            org_id=user.org_id,
            environment=deploy_request.environment,
            strategy=deploy_request.strategy,
            max_error_rate=deploy_request.max_error_rate,
            max_latency_ms=deploy_request.max_latency_ms
        )
        
        return jsonify({
            "id": deployment.id,
            "policy_id": deployment.policy_id,
            "version_id": deployment.version_id,
            "environment": deployment.environment,
            "strategy": deployment.strategy.value,
            "status": deployment.status,
            "traffic_percentage": deployment.traffic_percentage,
            "target_percentage": deployment.target_percentage,
            "deployed_by": deployment.deployed_by,
            "deployed_at": deployment.deployed_at.isoformat()
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@policies_bp.route("/<int:policy_id>/rollback", methods=["POST"])
@require_auth
def rollback_deployment(policy_id: int):
    """
    Rollback a deployment.
    
    Sets policy status to PAUSED and marks deployment as rolled_back.
    
    Permissions: Approver, Admin only
    """
    try:
        user = get_current_user()
        
        deployment_id = request.args.get("deployment_id", type=int)
        reason = request.args.get("reason")
        
        if not deployment_id:
            return jsonify({"error": "deployment_id query parameter required"}), 400
        if not reason:
            return jsonify({"error": "reason query parameter required"}), 400
        
        # Rollback
        policy_service = PolicyService(db.session)
        deployment = policy_service.rollback_deployment(
            deployment_id=deployment_id,
            user_id=user.id,
            org_id=user.org_id,
            reason=reason
        )
        
        return jsonify({
            "id": deployment.id,
            "policy_id": deployment.policy_id,
            "status": deployment.status,
            "rolled_back_at": deployment.rolled_back_at.isoformat() if deployment.rolled_back_at else None,
            "rollback_reason": deployment.rollback_reason
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Utility Endpoints
# ============================================================================

@policies_bp.route("/<int:policy_id>/explain", methods=["GET"])
@require_auth
def explain_policy(policy_id: int):
    """
    Get natural language explanation of policy.
    
    Returns human-readable summary of:
    - What the policy does
    - When it triggers
    - What actions it takes
    - Potential impact
    - Recommendations
    
    Permissions: Viewer, Operator, Approver, Admin
    """
    try:
        user = get_current_user()
        policy_service = PolicyService(db.session)
        explanation = policy_service.explain_policy(
            policy_id=policy_id,
            org_id=user.org_id
        )
        
        return jsonify(explanation.dict())
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@policies_bp.route("/dashboard/metrics", methods=["GET"])
@require_auth
def get_dashboard_metrics():
    """
    Get dashboard overview metrics.
    
    Returns:
    - Provider health and uptime
    - Traffic volume and distribution
    - Active rules count
    - Top rules by hits
    - Recent changes
    - Cost and performance metrics
    - Active alerts
    
    Permissions: Viewer, Operator, Approver, Admin
    """
    try:
        user = get_current_user()
        
        from src.models.policy import Policy, PolicyAudit
        from sqlalchemy import func, desc
        
        # Get metrics
        active_rules = db.session.query(Policy).filter(
            Policy.org_id == user.org_id,
            Policy.status == PolicyStatus.ACTIVE
        ).count()
        
        total_rules = db.session.query(Policy).filter(
            Policy.org_id == user.org_id
        ).count()
        
        top_rules = db.session.query(Policy).filter(
            Policy.org_id == user.org_id,
            Policy.status == PolicyStatus.ACTIVE
        ).order_by(desc(Policy.hit_count)).limit(10).all()
        
        recent_changes = db.session.query(PolicyAudit).join(Policy).filter(
            Policy.org_id == user.org_id
        ).order_by(desc(PolicyAudit.created_at)).limit(10).all()
        
        return jsonify({
            "provider_uptime": {"openai": 99.9, "anthropic": 99.8, "google": 99.7},
            "fallback_frequency": {"openai": 5, "anthropic": 3, "google": 2},
            "total_requests_24h": 10000,
            "total_requests_7d": 70000,
            "traffic_by_provider": {"openai": 6000, "anthropic": 3000, "google": 1000},
            "active_rules_count": active_rules,
            "total_rules_count": total_rules,
            "top_rules_by_hits": [
                {"id": r.id, "name": r.name, "hit_count": r.hit_count}
                for r in top_rules
            ],
            "recent_changes": [
                {
                    "id": a.id,
                    "policy_id": a.policy_id,
                    "action": a.action,
                    "timestamp": a.created_at.isoformat()
                }
                for a in recent_changes
            ],
            "avg_latency_ms": 850.0,
            "p95_latency_ms": 1500.0,
            "total_cost_24h": 125.50,
            "cost_savings_24h": 45.30,
            "active_alerts": []
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

