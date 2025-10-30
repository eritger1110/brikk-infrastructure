"""
Policy models for Brikk Rules Dashboard.

Enables non-technical users to create, simulate, approve, and deploy
agent coordination policies with enterprise-grade safety and audit trails.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, 
    ForeignKey, JSON, Index, CheckConstraint, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from src.database import Base


class PolicyStatus(str, Enum):
    """Policy lifecycle states."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class PolicyGoal(str, Enum):
    """Optimization goals for policies."""
    COST = "cost"
    LATENCY = "latency"
    QUALITY = "quality"
    COMPLIANCE = "compliance"
    CUSTOM = "custom"


class DeploymentStrategy(str, Enum):
    """Deployment rollout strategies."""
    IMMEDIATE = "immediate"
    CANARY_10 = "canary_10"
    CANARY_20 = "canary_20"
    CANARY_50 = "canary_50"
    GRADUAL = "gradual"


class Policy(Base):
    """
    Main policy table storing routing, cost, and compliance rules.
    
    Each policy defines conditions and actions for agent coordination.
    """
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    
    # Metadata
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    goal = Column(SQLEnum(PolicyGoal), nullable=False, default=PolicyGoal.COST)
    
    # Ownership
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False, index=True)
    
    # Status
    status = Column(SQLEnum(PolicyStatus), nullable=False, default=PolicyStatus.DRAFT, index=True)
    
    # Scope
    scope = Column(JSON, nullable=False)  # {apps: [], agents: [], languages: [], regions: []}
    
    # Rule definition (YAML stored as JSON for queryability)
    conditions = Column(JSON, nullable=False)  # [{type: "latency", operator: ">", value: 1000}]
    actions = Column(JSON, nullable=False)  # [{type: "route", provider: "openai", model: "gpt-4"}]
    
    # Priority (higher = evaluated first)
    priority = Column(Integer, default=100, nullable=False)
    
    # Metrics
    hit_count = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)
    last_hit_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deployed_at = Column(DateTime, nullable=True)
    
    # Tags for filtering
    tags = Column(JSON, default=list)  # ["production", "cost-optimization"]
    
    # Relationships
    versions = relationship("PolicyVersion", back_populates="policy", cascade="all, delete-orphan")
    approvals = relationship("PolicyApproval", back_populates="policy", cascade="all, delete-orphan")
    deployments = relationship("PolicyDeployment", back_populates="policy", cascade="all, delete-orphan")
    audits = relationship("PolicyAudit", back_populates="policy", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])
    
    __table_args__ = (
        Index("idx_policy_org_status", "org_id", "status"),
        Index("idx_policy_priority", "priority"),
    )


class PolicyVersion(Base):
    """
    Version history for policies (immutable snapshots).
    
    Every change creates a new version for audit and rollback.
    """
    __tablename__ = "policy_versions"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Version number (auto-incremented per policy)
    version = Column(Integer, nullable=False)
    
    # Snapshot of policy state
    name = Column(String(255), nullable=False)
    description = Column(Text)
    goal = Column(SQLEnum(PolicyGoal), nullable=False)
    scope = Column(JSON, nullable=False)
    conditions = Column(JSON, nullable=False)
    actions = Column(JSON, nullable=False)
    priority = Column(Integer, nullable=False)
    tags = Column(JSON, default=list)
    
    # Change tracking
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    change_summary = Column(Text)  # Human-readable description of changes
    
    # Simulation results (if simulated before deploy)
    simulation_results = Column(JSON, nullable=True)
    
    # Relationships
    policy = relationship("Policy", back_populates="versions")
    creator = relationship("User", foreign_keys=[created_by])
    
    __table_args__ = (
        Index("idx_policy_version", "policy_id", "version", unique=True),
    )


class PolicyApproval(Base):
    """
    Approval workflow for policy changes.
    
    Implements governance: Draft → Submit → Approve → Deploy.
    """
    __tablename__ = "policy_approvals"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("policy_versions.id"), nullable=False)
    
    # Approval request
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    request_notes = Column(Text)
    
    # Approval decision
    status = Column(String(50), nullable=False, default="pending")  # pending, approved, rejected
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text)
    
    # Deployment strategy (if approved)
    deployment_strategy = Column(SQLEnum(DeploymentStrategy), default=DeploymentStrategy.IMMEDIATE)
    
    # Relationships
    policy = relationship("Policy", back_populates="approvals")
    version = relationship("PolicyVersion")
    requester = relationship("User", foreign_keys=[requested_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    
    __table_args__ = (
        Index("idx_approval_status", "status"),
    )


class PolicyDeployment(Base):
    """
    Deployment history and canary rollout tracking.
    
    Supports gradual rollouts with auto-rollback on SLA breach.
    """
    __tablename__ = "policy_deployments"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("policy_versions.id"), nullable=False)
    approval_id = Column(Integer, ForeignKey("policy_approvals.id"), nullable=True)
    
    # Deployment metadata
    environment = Column(String(50), nullable=False, default="production")  # dev, staging, production
    strategy = Column(SQLEnum(DeploymentStrategy), nullable=False)
    
    # Canary rollout
    traffic_percentage = Column(Integer, default=100, nullable=False)  # 0-100
    target_percentage = Column(Integer, default=100, nullable=False)
    
    # Status
    status = Column(String(50), nullable=False, default="deploying")  # deploying, active, rolled_back, failed
    
    # Metrics
    requests_processed = Column(Integer, default=0)
    errors_encountered = Column(Integer, default=0)
    avg_latency_ms = Column(Integer, nullable=True)
    cost_impact = Column(JSON, nullable=True)  # {before: 0.05, after: 0.03, savings: 0.02}
    
    # Auto-rollback thresholds
    max_error_rate = Column(Integer, default=5)  # Percentage
    max_latency_ms = Column(Integer, default=5000)
    
    # Timestamps
    deployed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    deployed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    rolled_back_at = Column(DateTime, nullable=True)
    rollback_reason = Column(Text)
    
    # Relationships
    policy = relationship("Policy", back_populates="deployments")
    version = relationship("PolicyVersion")
    approval = relationship("PolicyApproval")
    deployer = relationship("User", foreign_keys=[deployed_by])
    
    __table_args__ = (
        Index("idx_deployment_env_status", "environment", "status"),
        CheckConstraint("traffic_percentage >= 0 AND traffic_percentage <= 100", name="check_traffic_percentage"),
    )


class PolicyAudit(Base):
    """
    Comprehensive audit log for all policy changes.
    
    Tracks who/what/when with full before/after diffs.
    """
    __tablename__ = "policy_audits"

    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Action details
    action = Column(String(100), nullable=False, index=True)  # created, updated, simulated, approved, deployed, rolled_back
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    actor_role = Column(String(50))  # operator, approver, admin
    
    # Change tracking
    before_state = Column(JSON, nullable=True)  # Full policy snapshot before change
    after_state = Column(JSON, nullable=True)  # Full policy snapshot after change
    diff = Column(JSON, nullable=True)  # Structured diff for UI display
    
    # Context
    notes = Column(Text)
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(String(500))
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    policy = relationship("Policy", back_populates="audits")
    actor = relationship("User", foreign_keys=[actor_id])
    
    __table_args__ = (
        Index("idx_audit_action_time", "action", "created_at"),
    )


class RBACRole(Base):
    """
    Role-based access control roles for policy management.
    
    Defines what actions each role can perform.
    """
    __tablename__ = "rbac_roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    
    # Permissions (JSON for flexibility)
    permissions = Column(JSON, nullable=False)  # {policies: {read: true, create: true, approve: false}}
    
    # Guardrails (hard limits that can't be bypassed)
    guardrails = Column(JSON, default=dict)  # {max_cost_ceiling: 1000, can_route_phi: false}
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    assignments = relationship("RBACAssignment", back_populates="role", cascade="all, delete-orphan")


class RBACAssignment(Base):
    """
    User-to-role assignments for policy management.
    
    Links users to their roles within organizations.
    """
    __tablename__ = "rbac_assignments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("rbac_roles.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Scope (optional: limit role to specific apps/agents)
    scope = Column(JSON, default=dict)  # {apps: ["app1"], agents: ["agent2"]}
    
    # Timestamps
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    role = relationship("RBACRole", back_populates="assignments")
    assigner = relationship("User", foreign_keys=[assigned_by])
    
    __table_args__ = (
        Index("idx_rbac_user_org", "user_id", "org_id", unique=True),
    )

