"""Rules Dashboard - Policy Management Tables

Revision ID: rules_dashboard_001
Revises: fix_api_keys_schema
Create Date: 2025-10-29 13:00:00.000000

Creates tables for the Brikk Rules Dashboard:
- policies: Main policy definitions
- policy_versions: Immutable version history
- policy_approvals: Approval workflow
- policy_deployments: Deployment tracking with canary support
- policy_audits: Comprehensive audit log
- rbac_roles: Role definitions
- rbac_assignments: User-to-role mappings
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'rules_dashboard_001'
down_revision = 'fix_api_keys_schema'
branch_labels = None
depends_on = None


def upgrade():
    # Create ENUM types
    op.execute("""
        CREATE TYPE policy_status AS ENUM (
            'draft', 'pending_approval', 'approved', 'active', 'paused', 'archived', 'rejected'
        );
    """)
    
    op.execute("""
        CREATE TYPE policy_goal AS ENUM (
            'cost', 'latency', 'quality', 'compliance', 'custom'
        );
    """)
    
    op.execute("""
        CREATE TYPE deployment_strategy AS ENUM (
            'immediate', 'canary_10', 'canary_20', 'canary_50', 'gradual'
        );
    """)
    
    # Create policies table
    op.create_table(
        'policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('goal', postgresql.ENUM(name='policy_goal'), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM(name='policy_status'), nullable=False),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('hit_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_hit_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('deployed_at', sa.DateTime(), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_policy_org_status', 'policies', ['org_id', 'status'])
    op.create_index('idx_policy_priority', 'policies', ['priority'])
    op.create_index(op.f('ix_policies_id'), 'policies', ['id'])
    op.create_index(op.f('ix_policies_name'), 'policies', ['name'])
    op.create_index(op.f('ix_policies_org_id'), 'policies', ['org_id'])
    op.create_index(op.f('ix_policies_status'), 'policies', ['status'])
    
    # Create policy_versions table
    op.create_table(
        'policy_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('goal', postgresql.ENUM(name='policy_goal'), nullable=False),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('simulation_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_policy_version', 'policy_versions', ['policy_id', 'version'], unique=True)
    op.create_index(op.f('ix_policy_versions_id'), 'policy_versions', ['id'])
    op.create_index(op.f('ix_policy_versions_policy_id'), 'policy_versions', ['policy_id'])
    
    # Create policy_approvals table
    op.create_table(
        'policy_approvals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('requested_by', sa.Integer(), nullable=False),
        sa.Column('requested_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('request_notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('deployment_strategy', postgresql.ENUM(name='deployment_strategy'), nullable=True),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['version_id'], ['policy_versions.id'], ),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_approval_status', 'policy_approvals', ['status'])
    op.create_index(op.f('ix_policy_approvals_id'), 'policy_approvals', ['id'])
    op.create_index(op.f('ix_policy_approvals_policy_id'), 'policy_approvals', ['policy_id'])
    
    # Create policy_deployments table
    op.create_table(
        'policy_deployments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('approval_id', sa.Integer(), nullable=True),
        sa.Column('environment', sa.String(length=50), nullable=False, server_default='production'),
        sa.Column('strategy', postgresql.ENUM(name='deployment_strategy'), nullable=False),
        sa.Column('traffic_percentage', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('target_percentage', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='deploying'),
        sa.Column('requests_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('errors_encountered', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_latency_ms', sa.Integer(), nullable=True),
        sa.Column('cost_impact', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('max_error_rate', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('max_latency_ms', sa.Integer(), nullable=False, server_default='5000'),
        sa.Column('deployed_by', sa.Integer(), nullable=False),
        sa.Column('deployed_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('rolled_back_at', sa.DateTime(), nullable=True),
        sa.Column('rollback_reason', sa.Text(), nullable=True),
        sa.CheckConstraint('traffic_percentage >= 0 AND traffic_percentage <= 100', name='check_traffic_percentage'),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['version_id'], ['policy_versions.id'], ),
        sa.ForeignKeyConstraint(['approval_id'], ['policy_approvals.id'], ),
        sa.ForeignKeyConstraint(['deployed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_deployment_env_status', 'policy_deployments', ['environment', 'status'])
    op.create_index(op.f('ix_policy_deployments_id'), 'policy_deployments', ['id'])
    op.create_index(op.f('ix_policy_deployments_policy_id'), 'policy_deployments', ['policy_id'])
    
    # Create policy_audits table
    op.create_table(
        'policy_audits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=False),
        sa.Column('actor_role', sa.String(length=50), nullable=True),
        sa.Column('before_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('after_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('diff', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['policy_id'], ['policies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_action_time', 'policy_audits', ['action', 'created_at'])
    op.create_index(op.f('ix_policy_audits_action'), 'policy_audits', ['action'])
    op.create_index(op.f('ix_policy_audits_created_at'), 'policy_audits', ['created_at'])
    op.create_index(op.f('ix_policy_audits_id'), 'policy_audits', ['id'])
    op.create_index(op.f('ix_policy_audits_policy_id'), 'policy_audits', ['policy_id'])
    
    # Create rbac_roles table
    op.create_table(
        'rbac_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('guardrails', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_rbac_roles_id'), 'rbac_roles', ['id'])
    op.create_index(op.f('ix_rbac_roles_name'), 'rbac_roles', ['name'], unique=True)
    
    # Create rbac_assignments table
    op.create_table(
        'rbac_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('assigned_by', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['rbac_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_rbac_user_org', 'rbac_assignments', ['user_id', 'org_id'], unique=True)
    op.create_index(op.f('ix_rbac_assignments_id'), 'rbac_assignments', ['id'])
    op.create_index(op.f('ix_rbac_assignments_org_id'), 'rbac_assignments', ['org_id'])
    op.create_index(op.f('ix_rbac_assignments_role_id'), 'rbac_assignments', ['role_id'])
    op.create_index(op.f('ix_rbac_assignments_user_id'), 'rbac_assignments', ['user_id'])
    
    # Insert default RBAC roles
    op.execute("""
        INSERT INTO rbac_roles (name, description, permissions, guardrails) VALUES
        ('viewer', 'Read-only access to rules and metrics', 
         '{"policies": {"read": true, "create": false, "update": false, "delete": false, "approve": false, "deploy": false}}',
         '{}'),
        ('operator', 'Create and edit draft rules, submit for approval',
         '{"policies": {"read": true, "create": true, "update": true, "delete": false, "approve": false, "deploy": false}}',
         '{"can_bypass_cost_ceiling": false, "can_route_phi": false, "can_disable_audit": false}'),
        ('approver', 'Review and deploy rules, manage canaries',
         '{"policies": {"read": true, "create": true, "update": true, "delete": false, "approve": true, "deploy": true}}',
         '{"can_bypass_cost_ceiling": false, "can_route_phi": false, "can_disable_audit": false}'),
        ('admin', 'Full access to all policy management features',
         '{"policies": {"read": true, "create": true, "update": true, "delete": true, "approve": true, "deploy": true}, "roles": {"manage": true}}',
         '{}');
    """)


def downgrade():
    # Drop tables in reverse order
    op.drop_index(op.f('ix_rbac_assignments_user_id'), table_name='rbac_assignments')
    op.drop_index(op.f('ix_rbac_assignments_role_id'), table_name='rbac_assignments')
    op.drop_index(op.f('ix_rbac_assignments_org_id'), table_name='rbac_assignments')
    op.drop_index(op.f('ix_rbac_assignments_id'), table_name='rbac_assignments')
    op.drop_index('idx_rbac_user_org', table_name='rbac_assignments')
    op.drop_table('rbac_assignments')
    
    op.drop_index(op.f('ix_rbac_roles_name'), table_name='rbac_roles')
    op.drop_index(op.f('ix_rbac_roles_id'), table_name='rbac_roles')
    op.drop_table('rbac_roles')
    
    op.drop_index(op.f('ix_policy_audits_policy_id'), table_name='policy_audits')
    op.drop_index(op.f('ix_policy_audits_id'), table_name='policy_audits')
    op.drop_index(op.f('ix_policy_audits_created_at'), table_name='policy_audits')
    op.drop_index(op.f('ix_policy_audits_action'), table_name='policy_audits')
    op.drop_index('idx_audit_action_time', table_name='policy_audits')
    op.drop_table('policy_audits')
    
    op.drop_index(op.f('ix_policy_deployments_policy_id'), table_name='policy_deployments')
    op.drop_index(op.f('ix_policy_deployments_id'), table_name='policy_deployments')
    op.drop_index('idx_deployment_env_status', table_name='policy_deployments')
    op.drop_table('policy_deployments')
    
    op.drop_index(op.f('ix_policy_approvals_policy_id'), table_name='policy_approvals')
    op.drop_index(op.f('ix_policy_approvals_id'), table_name='policy_approvals')
    op.drop_index('idx_approval_status', table_name='policy_approvals')
    op.drop_table('policy_approvals')
    
    op.drop_index(op.f('ix_policy_versions_policy_id'), table_name='policy_versions')
    op.drop_index(op.f('ix_policy_versions_id'), table_name='policy_versions')
    op.drop_index('idx_policy_version', table_name='policy_versions')
    op.drop_table('policy_versions')
    
    op.drop_index(op.f('ix_policies_status'), table_name='policies')
    op.drop_index(op.f('ix_policies_org_id'), table_name='policies')
    op.drop_index(op.f('ix_policies_name'), table_name='policies')
    op.drop_index(op.f('ix_policies_id'), table_name='policies')
    op.drop_index('idx_policy_priority', table_name='policies')
    op.drop_index('idx_policy_org_status', table_name='policies')
    op.drop_table('policies')
    
    # Drop ENUM types
    op.execute("DROP TYPE deployment_strategy;")
    op.execute("DROP TYPE policy_goal;")
    op.execute("DROP TYPE policy_status;")

