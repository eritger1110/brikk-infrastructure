"""
Policy Service - Business logic for Rules Dashboard.

Handles policy CRUD, simulation, approval workflow, and deployment.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
import json

from src.models.policy import (
    Policy, PolicyVersion, PolicyApproval, PolicyDeployment,
    PolicyAudit, RBACRole, RBACAssignment,
    PolicyStatus, PolicyGoal, DeploymentStrategy
)
from src.models.user import User
from src.models.usage_event import UsageEvent
from src.schemas.policy import (
    PolicyCreate, PolicyUpdate, PolicySimulateRequest,
    SimulationResult, PolicyExplainResponse
)


class PolicyService:
    """Service layer for policy management."""

    def __init__(self, db: Session):
        self.db = db

    # ============================================================================
    # CRUD Operations
    # ============================================================================

    def create_policy(
        self,
        policy_data: PolicyCreate,
        user_id: int,
        org_id: int
    ) -> Policy:
        """Create a new draft policy."""
        # Create policy
        policy = Policy(
            name=policy_data.name,
            description=policy_data.description,
            goal=policy_data.goal,
            scope=policy_data.scope.dict(),
            conditions=[c.dict() for c in policy_data.conditions],
            actions=[a.dict() for a in policy_data.actions],
            priority=policy_data.priority,
            tags=policy_data.tags or [],
            created_by=user_id,
            org_id=org_id,
            status=PolicyStatus.DRAFT
        )
        self.db.add(policy)
        self.db.flush()

        # Create initial version
        self._create_version(
            policy=policy,
            user_id=user_id,
            change_summary="Initial policy creation"
        )

        # Create audit log
        self._create_audit(
            policy_id=policy.id,
            action="created",
            actor_id=user_id,
            after_state=self._policy_to_dict(policy),
            notes=f"Created policy: {policy.name}"
        )

        self.db.commit()
        self.db.refresh(policy)
        return policy

    def get_policy(self, policy_id: int, org_id: int) -> Optional[Policy]:
        """Get policy by ID (org-scoped)."""
        return self.db.query(Policy).filter(
            Policy.id == policy_id,
            Policy.org_id == org_id
        ).first()

    def list_policies(
        self,
        org_id: int,
        status: Optional[PolicyStatus] = None,
        tags: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[Policy], int]:
        """List policies with filtering and pagination."""
        query = self.db.query(Policy).filter(Policy.org_id == org_id)

        if status:
            query = query.filter(Policy.status == status)

        if tags:
            # Filter by tags (policies must have at least one matching tag)
            query = query.filter(
                or_(*[Policy.tags.contains([tag]) for tag in tags])
            )

        total = query.count()
        policies = query.order_by(desc(Policy.updated_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return policies, total

    def update_policy(
        self,
        policy_id: int,
        policy_data: PolicyUpdate,
        user_id: int,
        org_id: int
    ) -> Policy:
        """Update an existing policy."""
        policy = self.get_policy(policy_id, org_id)
        if not policy:
            raise ValueError("Policy not found")

        if policy.status not in [PolicyStatus.DRAFT, PolicyStatus.PAUSED]:
            raise ValueError("Can only update draft or paused policies")

        # Capture before state
        before_state = self._policy_to_dict(policy)

        # Update fields
        update_data = policy_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "scope" and value:
                setattr(policy, field, value.dict())
            elif field in ["conditions", "actions"] and value:
                setattr(policy, field, [item.dict() for item in value])
            else:
                setattr(policy, field, value)

        policy.updated_at = datetime.utcnow()

        # Create new version
        self._create_version(
            policy=policy,
            user_id=user_id,
            change_summary=f"Updated policy: {', '.join(update_data.keys())}"
        )

        # Create audit log
        self._create_audit(
            policy_id=policy.id,
            action="updated",
            actor_id=user_id,
            before_state=before_state,
            after_state=self._policy_to_dict(policy),
            notes=f"Updated fields: {', '.join(update_data.keys())}"
        )

        self.db.commit()
        self.db.refresh(policy)
        return policy

    def delete_policy(self, policy_id: int, user_id: int, org_id: int) -> bool:
        """Delete a draft policy."""
        policy = self.get_policy(policy_id, org_id)
        if not policy:
            return False

        if policy.status != PolicyStatus.DRAFT:
            raise ValueError("Can only delete draft policies")

        # Create audit log before deletion
        self._create_audit(
            policy_id=policy.id,
            action="deleted",
            actor_id=user_id,
            before_state=self._policy_to_dict(policy),
            notes=f"Deleted policy: {policy.name}"
        )

        self.db.delete(policy)
        self.db.commit()
        return True

    # ============================================================================
    # Simulation
    # ============================================================================

    def simulate_policy(
        self,
        policy_id: int,
        simulate_request: PolicySimulateRequest,
        org_id: int
    ) -> SimulationResult:
        """
        Simulate policy against recent traffic.
        
        Analyzes last N minutes of usage events to predict impact.
        """
        policy = self.get_policy(policy_id, org_id)
        if not policy:
            raise ValueError("Policy not found")

        # Get recent usage events
        cutoff_time = datetime.utcnow() - timedelta(
            minutes=simulate_request.time_window_minutes
        )
        
        events_query = self.db.query(UsageEvent).filter(
            UsageEvent.org_id == org_id,
            UsageEvent.created_at >= cutoff_time
        )

        if simulate_request.sample_size:
            events_query = events_query.limit(simulate_request.sample_size)

        events = events_query.all()
        total_requests = len(events)

        if total_requests == 0:
            return SimulationResult(
                policy_id=policy_id,
                time_window_minutes=simulate_request.time_window_minutes,
                total_requests_analyzed=0,
                requests_matched=0,
                hit_rate_percentage=0.0,
                routing_changes={},
                estimated_latency_change_ms=None,
                estimated_cost_change=None,
                estimated_cost_savings_percentage=None,
                risk_flags=[],
                compliance_violations=[],
                sample_matches=[],
                recommendation="insufficient_data"
            )

        # Evaluate policy against each event
        matched_events = []
        routing_changes = {}
        total_latency_before = 0
        total_latency_after = 0
        total_cost_before = 0
        total_cost_after = 0

        for event in events:
            if self._evaluate_conditions(policy.conditions, event):
                matched_events.append(event)
                
                # Simulate routing change
                action = policy.actions[0] if policy.actions else {}
                if action.get("type") == "route":
                    new_provider = action.get("provider", "unknown")
                    routing_changes[new_provider] = routing_changes.get(new_provider, 0) + 1
                    
                    # Estimate latency/cost impact (simplified)
                    total_latency_before += event.latency_ms or 0
                    total_latency_after += self._estimate_latency(new_provider)
                    
                    total_cost_before += event.cost or 0.0
                    total_cost_after += self._estimate_cost(new_provider, event)

        requests_matched = len(matched_events)
        hit_rate = (requests_matched / total_requests) * 100 if total_requests > 0 else 0

        # Calculate impact
        avg_latency_change = None
        cost_change = None
        cost_savings_pct = None

        if requests_matched > 0:
            avg_latency_change = (total_latency_after - total_latency_before) / requests_matched
            cost_change = total_cost_after - total_cost_before
            if total_cost_before > 0:
                cost_savings_pct = ((total_cost_before - total_cost_after) / total_cost_before) * 100

        # Identify risks
        risk_flags = []
        compliance_violations = []

        if hit_rate > 80:
            risk_flags.append("high_hit_rate")
        if avg_latency_change and avg_latency_change > 500:
            risk_flags.append("significant_latency_increase")
        if cost_change and cost_change > 100:
            risk_flags.append("high_cost_increase")

        # Recommendation
        if len(risk_flags) == 0:
            recommendation = "safe_to_deploy"
        elif len(risk_flags) <= 2:
            recommendation = "review_required"
        else:
            recommendation = "high_risk"

        # Sample matches (first 10)
        sample_matches = [
            {
                "event_id": e.id,
                "timestamp": e.created_at.isoformat(),
                "latency_ms": e.latency_ms,
                "cost": e.cost,
                "provider": e.provider
            }
            for e in matched_events[:10]
        ]

        return SimulationResult(
            policy_id=policy_id,
            time_window_minutes=simulate_request.time_window_minutes,
            total_requests_analyzed=total_requests,
            requests_matched=requests_matched,
            hit_rate_percentage=round(hit_rate, 2),
            routing_changes=routing_changes,
            estimated_latency_change_ms=round(avg_latency_change, 2) if avg_latency_change else None,
            estimated_cost_change=round(cost_change, 4) if cost_change else None,
            estimated_cost_savings_percentage=round(cost_savings_pct, 2) if cost_savings_pct else None,
            risk_flags=risk_flags,
            compliance_violations=compliance_violations,
            sample_matches=sample_matches,
            recommendation=recommendation
        )

    # ============================================================================
    # Approval Workflow
    # ============================================================================

    def submit_for_approval(
        self,
        policy_id: int,
        user_id: int,
        org_id: int,
        notes: Optional[str] = None,
        deployment_strategy: DeploymentStrategy = DeploymentStrategy.IMMEDIATE
    ) -> PolicyApproval:
        """Submit policy for approval."""
        policy = self.get_policy(policy_id, org_id)
        if not policy:
            raise ValueError("Policy not found")

        if policy.status != PolicyStatus.DRAFT:
            raise ValueError("Can only submit draft policies for approval")

        # Get latest version
        latest_version = self.db.query(PolicyVersion).filter(
            PolicyVersion.policy_id == policy_id
        ).order_by(desc(PolicyVersion.version)).first()

        # Create approval request
        approval = PolicyApproval(
            policy_id=policy_id,
            version_id=latest_version.id,
            requested_by=user_id,
            request_notes=notes,
            deployment_strategy=deployment_strategy
        )
        self.db.add(approval)

        # Update policy status
        policy.status = PolicyStatus.PENDING_APPROVAL
        policy.updated_at = datetime.utcnow()

        # Create audit log
        self._create_audit(
            policy_id=policy.id,
            action="submitted_for_approval",
            actor_id=user_id,
            notes=f"Submitted for approval: {notes or 'No notes'}"
        )

        self.db.commit()
        self.db.refresh(approval)
        return approval

    def approve_policy(
        self,
        policy_id: int,
        approval_id: int,
        user_id: int,
        org_id: int,
        approved: bool,
        notes: Optional[str] = None
    ) -> PolicyApproval:
        """Approve or reject a policy."""
        policy = self.get_policy(policy_id, org_id)
        if not policy:
            raise ValueError("Policy not found")

        approval = self.db.query(PolicyApproval).filter(
            PolicyApproval.id == approval_id,
            PolicyApproval.policy_id == policy_id
        ).first()

        if not approval:
            raise ValueError("Approval request not found")

        if approval.status != "pending":
            raise ValueError("Approval already processed")

        # Update approval
        approval.status = "approved" if approved else "rejected"
        approval.reviewed_by = user_id
        approval.reviewed_at = datetime.utcnow()
        approval.review_notes = notes

        # Update policy status
        if approved:
            policy.status = PolicyStatus.APPROVED
        else:
            policy.status = PolicyStatus.REJECTED

        policy.updated_at = datetime.utcnow()

        # Create audit log
        self._create_audit(
            policy_id=policy.id,
            action="approved" if approved else "rejected",
            actor_id=user_id,
            notes=f"{'Approved' if approved else 'Rejected'}: {notes or 'No notes'}"
        )

        self.db.commit()
        self.db.refresh(approval)
        return approval

    # ============================================================================
    # Deployment
    # ============================================================================

    def deploy_policy(
        self,
        policy_id: int,
        user_id: int,
        org_id: int,
        environment: str = "production",
        strategy: DeploymentStrategy = DeploymentStrategy.IMMEDIATE,
        max_error_rate: int = 5,
        max_latency_ms: int = 5000
    ) -> PolicyDeployment:
        """Deploy an approved policy."""
        policy = self.get_policy(policy_id, org_id)
        if not policy:
            raise ValueError("Policy not found")

        if policy.status != PolicyStatus.APPROVED:
            raise ValueError("Can only deploy approved policies")

        # Get latest version
        latest_version = self.db.query(PolicyVersion).filter(
            PolicyVersion.policy_id == policy_id
        ).order_by(desc(PolicyVersion.version)).first()

        # Determine traffic percentage based on strategy
        traffic_pct = {
            DeploymentStrategy.IMMEDIATE: 100,
            DeploymentStrategy.CANARY_10: 10,
            DeploymentStrategy.CANARY_20: 20,
            DeploymentStrategy.CANARY_50: 50,
            DeploymentStrategy.GRADUAL: 10
        }.get(strategy, 100)

        # Create deployment
        deployment = PolicyDeployment(
            policy_id=policy_id,
            version_id=latest_version.id,
            environment=environment,
            strategy=strategy,
            traffic_percentage=traffic_pct,
            target_percentage=100,
            max_error_rate=max_error_rate,
            max_latency_ms=max_latency_ms,
            deployed_by=user_id,
            status="active" if traffic_pct == 100 else "deploying"
        )
        self.db.add(deployment)

        # Update policy status
        policy.status = PolicyStatus.ACTIVE
        policy.deployed_at = datetime.utcnow()
        policy.updated_at = datetime.utcnow()

        # Create audit log
        self._create_audit(
            policy_id=policy.id,
            action="deployed",
            actor_id=user_id,
            notes=f"Deployed to {environment} with {strategy.value} strategy"
        )

        self.db.commit()
        self.db.refresh(deployment)
        return deployment

    def rollback_deployment(
        self,
        deployment_id: int,
        user_id: int,
        org_id: int,
        reason: str
    ) -> PolicyDeployment:
        """Rollback a deployment."""
        deployment = self.db.query(PolicyDeployment).filter(
            PolicyDeployment.id == deployment_id
        ).first()

        if not deployment:
            raise ValueError("Deployment not found")

        policy = self.get_policy(deployment.policy_id, org_id)
        if not policy:
            raise ValueError("Policy not found")

        # Update deployment
        deployment.status = "rolled_back"
        deployment.rolled_back_at = datetime.utcnow()
        deployment.rollback_reason = reason

        # Update policy status
        policy.status = PolicyStatus.PAUSED
        policy.updated_at = datetime.utcnow()

        # Create audit log
        self._create_audit(
            policy_id=policy.id,
            action="rolled_back",
            actor_id=user_id,
            notes=f"Rolled back deployment: {reason}"
        )

        self.db.commit()
        self.db.refresh(deployment)
        return deployment

    # ============================================================================
    # Explain Policy (Natural Language)
    # ============================================================================

    def explain_policy(self, policy_id: int, org_id: int) -> PolicyExplainResponse:
        """Generate natural language explanation of policy."""
        policy = self.get_policy(policy_id, org_id)
        if not policy:
            raise ValueError("Policy not found")

        # Generate summary
        summary = f"{policy.name}: {policy.description or 'No description'}"

        # Explain conditions
        conditions_explained = []
        for cond in policy.conditions:
            cond_text = f"When {cond['type']} {cond['operator']} {cond['value']}"
            conditions_explained.append(cond_text)

        # Explain actions
        actions_explained = []
        for action in policy.actions:
            if action['type'] == 'route':
                action_text = f"Route to {action.get('provider', 'unknown')} using {action.get('model', 'default model')}"
            else:
                action_text = f"{action['type'].capitalize()} with parameters: {action.get('parameters', {})}"
            actions_explained.append(action_text)

        # Detailed explanation
        detailed = f"""
This policy optimizes for {policy.goal.value}.

**Scope:** Applies to {', '.join(policy.scope.get('apps', ['all apps']))}

**Conditions:** {' AND '.join(conditions_explained)}

**Actions:** {', '.join(actions_explained)}

**Priority:** {policy.priority} (higher priority policies are evaluated first)
        """.strip()

        # Potential impact
        impact = f"This policy will affect requests matching the conditions above. "
        if policy.goal == PolicyGoal.COST:
            impact += "It aims to reduce costs by routing to more economical providers."
        elif policy.goal == PolicyGoal.LATENCY:
            impact += "It aims to reduce latency by routing to faster providers."
        elif policy.goal == PolicyGoal.QUALITY:
            impact += "It aims to improve quality by routing to higher-quality providers."
        elif policy.goal == PolicyGoal.COMPLIANCE:
            impact += "It ensures compliance by enforcing data handling rules."

        # Recommendations
        recommendations = [
            "Run a simulation to see predicted impact on recent traffic",
            "Start with a canary deployment (10-20%) to minimize risk",
            "Monitor error rates and latency after deployment"
        ]

        return PolicyExplainResponse(
            policy_id=policy.id,
            summary=summary,
            detailed_explanation=detailed,
            conditions_explained=conditions_explained,
            actions_explained=actions_explained,
            potential_impact=impact,
            recommendations=recommendations
        )

    # ============================================================================
    # Helper Methods
    # ============================================================================

    def _create_version(
        self,
        policy: Policy,
        user_id: int,
        change_summary: str,
        simulation_results: Optional[Dict] = None
    ) -> PolicyVersion:
        """Create a new policy version."""
        # Get next version number
        max_version = self.db.query(func.max(PolicyVersion.version)).filter(
            PolicyVersion.policy_id == policy.id
        ).scalar() or 0

        version = PolicyVersion(
            policy_id=policy.id,
            version=max_version + 1,
            name=policy.name,
            description=policy.description,
            goal=policy.goal,
            scope=policy.scope,
            conditions=policy.conditions,
            actions=policy.actions,
            priority=policy.priority,
            tags=policy.tags,
            created_by=user_id,
            change_summary=change_summary,
            simulation_results=simulation_results
        )
        self.db.add(version)
        return version

    def _create_audit(
        self,
        policy_id: int,
        action: str,
        actor_id: int,
        before_state: Optional[Dict] = None,
        after_state: Optional[Dict] = None,
        notes: Optional[str] = None
    ) -> PolicyAudit:
        """Create an audit log entry."""
        audit = PolicyAudit(
            policy_id=policy_id,
            action=action,
            actor_id=actor_id,
            before_state=before_state,
            after_state=after_state,
            notes=notes
        )
        self.db.add(audit)
        return audit

    def _policy_to_dict(self, policy: Policy) -> Dict[str, Any]:
        """Convert policy to dictionary for audit."""
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
            "tags": policy.tags
        }

    def _evaluate_conditions(
        self,
        conditions: List[Dict],
        event: UsageEvent
    ) -> bool:
        """Evaluate if event matches policy conditions."""
        for cond in conditions:
            cond_type = cond.get("type")
            operator = cond.get("operator")
            value = cond.get("value")

            # Get event value based on condition type
            if cond_type == "latency":
                event_value = event.latency_ms or 0
            elif cond_type == "cost":
                event_value = event.cost or 0.0
            elif cond_type == "provider":
                event_value = event.provider
            else:
                continue

            # Evaluate condition
            if operator == ">":
                if not (event_value > value):
                    return False
            elif operator == "<":
                if not (event_value < value):
                    return False
            elif operator == "==":
                if not (event_value == value):
                    return False
            elif operator == "!=":
                if not (event_value != value):
                    return False

        return True

    def _estimate_latency(self, provider: str) -> float:
        """Estimate latency for a provider (simplified)."""
        # In production, this would query actual metrics
        latency_map = {
            "openai": 800,
            "anthropic": 600,
            "google": 700,
            "cohere": 750
        }
        return latency_map.get(provider, 1000)

    def _estimate_cost(self, provider: str, event: UsageEvent) -> float:
        """Estimate cost for a provider (simplified)."""
        # In production, this would use actual pricing models
        cost_map = {
            "openai": 0.03,
            "anthropic": 0.025,
            "google": 0.02,
            "cohere": 0.015
        }
        base_cost = cost_map.get(provider, 0.05)
        tokens = event.tokens_used or 1000
        return (tokens / 1000) * base_cost

