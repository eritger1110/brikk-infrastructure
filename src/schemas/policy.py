"""
Pydantic schemas for Policy API.

Request/response validation models for the Rules Dashboard.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


# Enums
class PolicyStatusEnum(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class PolicyGoalEnum(str, Enum):
    COST = "cost"
    LATENCY = "latency"
    QUALITY = "quality"
    COMPLIANCE = "compliance"
    CUSTOM = "custom"


class DeploymentStrategyEnum(str, Enum):
    IMMEDIATE = "immediate"
    CANARY_10 = "canary_10"
    CANARY_20 = "canary_20"
    CANARY_50 = "canary_50"
    GRADUAL = "gradual"


# Nested schemas for policy definition
class PolicyScope(BaseModel):
    """Scope definition for where policy applies."""
    apps: Optional[List[str]] = Field(default_factory=list, description="App IDs or names")
    agents: Optional[List[str]] = Field(default_factory=list, description="Agent IDs or names")
    languages: Optional[List[str]] = Field(default_factory=list, description="Programming languages")
    regions: Optional[List[str]] = Field(default_factory=list, description="Geographic regions")
    environments: Optional[List[str]] = Field(default_factory=list, description="Environments (dev, staging, prod)")


class PolicyCondition(BaseModel):
    """Condition that triggers policy actions."""
    type: str = Field(..., description="Condition type (latency, cost, pii, provider_health, etc.)")
    operator: str = Field(..., description="Comparison operator (>, <, ==, !=, contains, etc.)")
    value: Any = Field(..., description="Threshold value")
    field: Optional[str] = Field(None, description="Field to evaluate (for complex conditions)")


class PolicyAction(BaseModel):
    """Action to take when conditions are met."""
    type: str = Field(..., description="Action type (route, redact, downgrade, notify, block, etc.)")
    provider: Optional[str] = Field(None, description="Provider to route to")
    model: Optional[str] = Field(None, description="Model to use")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Action parameters")


# Request schemas
class PolicyCreate(BaseModel):
    """Request schema for creating a new policy."""
    name: str = Field(..., min_length=1, max_length=255, description="Policy name")
    description: Optional[str] = Field(None, description="Policy description")
    goal: PolicyGoalEnum = Field(..., description="Optimization goal")
    scope: PolicyScope = Field(..., description="Where policy applies")
    conditions: List[PolicyCondition] = Field(..., min_items=1, description="Conditions to evaluate")
    actions: List[PolicyAction] = Field(..., min_items=1, description="Actions to take")
    priority: int = Field(default=100, ge=0, le=1000, description="Priority (higher = evaluated first)")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags for filtering")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "High Latency Fallback",
                "description": "Route to faster provider when latency exceeds 2s",
                "goal": "latency",
                "scope": {
                    "apps": ["chatbot"],
                    "agents": ["customer-support"],
                    "environments": ["production"]
                },
                "conditions": [
                    {"type": "latency", "operator": ">", "value": 2000}
                ],
                "actions": [
                    {"type": "route", "provider": "anthropic", "model": "claude-3-haiku"}
                ],
                "priority": 200,
                "tags": ["latency-optimization", "production"]
            }
        }


class PolicyUpdate(BaseModel):
    """Request schema for updating an existing policy."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    goal: Optional[PolicyGoalEnum] = None
    scope: Optional[PolicyScope] = None
    conditions: Optional[List[PolicyCondition]] = None
    actions: Optional[List[PolicyAction]] = None
    priority: Optional[int] = Field(None, ge=0, le=1000)
    tags: Optional[List[str]] = None
    status: Optional[PolicyStatusEnum] = None


class PolicySimulateRequest(BaseModel):
    """Request schema for simulating a policy."""
    time_window_minutes: int = Field(default=60, ge=1, le=1440, description="Time window to analyze (1-1440 min)")
    sample_size: Optional[int] = Field(None, ge=1, le=10000, description="Max requests to analyze")


class PolicyApprovalRequest(BaseModel):
    """Request schema for submitting policy for approval."""
    notes: Optional[str] = Field(None, description="Notes for approver")
    deployment_strategy: DeploymentStrategyEnum = Field(default=DeploymentStrategyEnum.IMMEDIATE)


class PolicyApprovalDecision(BaseModel):
    """Request schema for approving/rejecting a policy."""
    approved: bool = Field(..., description="Approval decision")
    notes: Optional[str] = Field(None, description="Review notes")
    deployment_strategy: Optional[DeploymentStrategyEnum] = None


class PolicyDeployRequest(BaseModel):
    """Request schema for deploying a policy."""
    environment: str = Field(default="production", description="Target environment")
    strategy: DeploymentStrategyEnum = Field(default=DeploymentStrategyEnum.IMMEDIATE)
    max_error_rate: int = Field(default=5, ge=0, le=100, description="Max error rate % before rollback")
    max_latency_ms: int = Field(default=5000, ge=0, description="Max latency before rollback")


# Response schemas
class PolicyResponse(BaseModel):
    """Response schema for policy details."""
    id: int
    name: str
    description: Optional[str]
    goal: PolicyGoalEnum
    status: PolicyStatusEnum
    scope: PolicyScope
    conditions: List[PolicyCondition]
    actions: List[PolicyAction]
    priority: int
    tags: List[str]
    
    # Metrics
    hit_count: int
    error_count: int
    last_hit_at: Optional[datetime]
    
    # Metadata
    created_by: int
    org_id: int
    created_at: datetime
    updated_at: datetime
    deployed_at: Optional[datetime]
    
    # Human-readable summary
    summary: Optional[str] = None

    class Config:
        from_attributes = True


class PolicyListResponse(BaseModel):
    """Response schema for policy list."""
    policies: List[PolicyResponse]
    total: int
    page: int
    page_size: int


class PolicyVersionResponse(BaseModel):
    """Response schema for policy version."""
    id: int
    policy_id: int
    version: int
    name: str
    description: Optional[str]
    goal: PolicyGoalEnum
    scope: PolicyScope
    conditions: List[PolicyCondition]
    actions: List[PolicyAction]
    priority: int
    tags: List[str]
    created_by: int
    created_at: datetime
    change_summary: Optional[str]
    simulation_results: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


class SimulationResult(BaseModel):
    """Response schema for policy simulation."""
    policy_id: int
    time_window_minutes: int
    total_requests_analyzed: int
    requests_matched: int
    hit_rate_percentage: float
    
    # Impact analysis
    routing_changes: Dict[str, int]  # {provider: count}
    estimated_latency_change_ms: Optional[float]
    estimated_cost_change: Optional[float]
    estimated_cost_savings_percentage: Optional[float]
    
    # Risk flags
    risk_flags: List[str]  # ["high_error_rate", "pii_exposure", etc.]
    compliance_violations: List[str]
    
    # Sample matched requests
    sample_matches: List[Dict[str, Any]]
    
    # Recommendation
    recommendation: str  # "safe_to_deploy", "review_required", "high_risk"


class PolicyApprovalResponse(BaseModel):
    """Response schema for policy approval."""
    id: int
    policy_id: int
    version_id: int
    status: str
    requested_by: int
    requested_at: datetime
    request_notes: Optional[str]
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]
    deployment_strategy: Optional[DeploymentStrategyEnum]

    class Config:
        from_attributes = True


class PolicyDeploymentResponse(BaseModel):
    """Response schema for policy deployment."""
    id: int
    policy_id: int
    version_id: int
    environment: str
    strategy: DeploymentStrategyEnum
    status: str
    traffic_percentage: int
    target_percentage: int
    
    # Metrics
    requests_processed: int
    errors_encountered: int
    avg_latency_ms: Optional[int]
    cost_impact: Optional[Dict[str, float]]
    
    # Timestamps
    deployed_by: int
    deployed_at: datetime
    completed_at: Optional[datetime]
    rolled_back_at: Optional[datetime]
    rollback_reason: Optional[str]

    class Config:
        from_attributes = True


class PolicyAuditResponse(BaseModel):
    """Response schema for policy audit log."""
    id: int
    policy_id: int
    action: str
    actor_id: int
    actor_role: Optional[str]
    before_state: Optional[Dict[str, Any]]
    after_state: Optional[Dict[str, Any]]
    diff: Optional[Dict[str, Any]]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PolicyAuditListResponse(BaseModel):
    """Response schema for audit log list."""
    audits: List[PolicyAuditResponse]
    total: int
    page: int
    page_size: int


class RBACRoleResponse(BaseModel):
    """Response schema for RBAC role."""
    id: int
    name: str
    description: Optional[str]
    permissions: Dict[str, Any]
    guardrails: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DashboardMetrics(BaseModel):
    """Response schema for dashboard overview metrics."""
    # Provider health
    provider_uptime: Dict[str, float]  # {provider: uptime_percentage}
    fallback_frequency: Dict[str, int]  # {provider: fallback_count}
    
    # Traffic
    total_requests_24h: int
    total_requests_7d: int
    traffic_by_provider: Dict[str, int]
    
    # Rules
    active_rules_count: int
    total_rules_count: int
    top_rules_by_hits: List[Dict[str, Any]]  # [{id, name, hit_count}]
    recent_changes: List[Dict[str, Any]]  # [{id, name, action, timestamp}]
    
    # Cost & Performance
    avg_latency_ms: float
    p95_latency_ms: float
    total_cost_24h: float
    cost_savings_24h: float
    
    # Alerts
    active_alerts: List[Dict[str, Any]]  # [{type, message, severity}]


class PolicyExplainResponse(BaseModel):
    """Response schema for natural language policy explanation."""
    policy_id: int
    summary: str
    detailed_explanation: str
    conditions_explained: List[str]
    actions_explained: List[str]
    potential_impact: str
    recommendations: List[str]

