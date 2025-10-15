"""baseline_schema

Revision ID: b07a366647c3
Revises: 
Create Date: 2025-10-14 15:56:17.740191

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b07a366647c3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for Brikk infrastructure (baseline schema)."""
    
    # Organizations table (must be first due to FK dependencies)
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('billing_email', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_organization_id'), 'users', ['organization_id'], unique=False)
    
    # Agents table
    op.create_table(
        'agents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('capabilities', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('specialization', sa.String(length=200), nullable=True),
        sa.Column('performance_score', sa.Float(), nullable=True),
        sa.Column('endpoint_url', sa.String(length=500), nullable=True),
        sa.Column('api_key', sa.String(length=100), nullable=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('total_coordinations', sa.Integer(), nullable=True),
        sa.Column('successful_coordinations', sa.Integer(), nullable=True),
        sa.Column('average_response_time', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agents_organization_id'), 'agents', ['organization_id'], unique=False)
    
    # Agent Services table (with String agent_id - the correct type)
    op.create_table(
        'agent_services',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('agent_id', sa.String(length=36), nullable=False),  # String, not Integer!
        sa.Column('service_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('endpoint', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Agent Capabilities table
    op.create_table(
        'agent_capabilities',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('agent_id', sa.String(length=36), nullable=False),
        sa.Column('capability_name', sa.String(length=100), nullable=False),
        sa.Column('capability_value', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Agent Performance table
    op.create_table(
        'agent_performance',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('agent_id', sa.String(length=36), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # API Keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('agent_id', sa.String(length=36), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Coordinations table
    op.create_table(
        'coordinations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workflow_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('initiator_agent_id', sa.String(length=36), nullable=True),
        sa.Column('participating_agents', sa.Text(), nullable=True),
        sa.Column('workflow_steps', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('total_duration', sa.Float(), nullable=True),
        sa.Column('result_data', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('security_level', sa.String(length=20), nullable=True),
        sa.Column('audit_trail', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['initiator_agent_id'], ['agents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Security Events table
    op.create_table(
        'security_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('user_id', sa.String(length=100), nullable=True),
        sa.Column('agent_id', sa.String(length=36), nullable=True),
        sa.Column('resource_accessed', sa.String(length=200), nullable=True),
        sa.Column('access_granted', sa.Boolean(), nullable=True),
        sa.Column('security_level_required', sa.String(length=20), nullable=True),
        sa.Column('security_level_provided', sa.String(length=20), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('event_data', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Ledger Accounts table (for economy system)
    op.create_table(
        'ledger_accounts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('account_type', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('balance', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Ledger Entries table
    op.create_table(
        'ledger_entries',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('account_id', sa.String(length=36), nullable=False),
        sa.Column('amount', sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column('entry_type', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['ledger_accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Org Balances table
    op.create_table(
        'org_balances',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('balance', sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id')
    )
    
    # Transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('from_agent_id', sa.String(length=36), nullable=True),
        sa.Column('to_agent_id', sa.String(length=36), nullable=True),
        sa.Column('amount', sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['from_agent_id'], ['agents.id'], ),
        sa.ForeignKeyConstraint(['to_agent_id'], ['agents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Reputation Scores table
    op.create_table(
        'reputation_scores',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('agent_id', sa.String(length=36), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Message Logs table
    op.create_table(
        'message_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('from_agent_id', sa.String(length=36), nullable=True),
        sa.Column('to_agent_id', sa.String(length=36), nullable=True),
        sa.Column('message_content', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['from_agent_id'], ['agents.id'], ),
        sa.ForeignKeyConstraint(['to_agent_id'], ['agents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Audit Logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=True),
        sa.Column('resource_id', sa.String(length=36), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Customer Profiles table
    op.create_table(
        'customer_profiles',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Purchases table
    op.create_table(
        'purchases',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('organization_id', sa.String(length=36), nullable=False),
        sa.Column('amount', sa.Numeric(precision=20, scale=2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Webhooks table
    op.create_table(
        'webhooks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Webhook Events table
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('webhook_id', sa.String(length=36), nullable=False),
        sa.Column('payload', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Workflows table
    op.create_table(
        'workflows',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Workflow Steps table
    op.create_table(
        'workflow_steps',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workflow_id', sa.String(length=36), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('step_type', sa.String(length=100), nullable=False),
        sa.Column('config', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Workflow Executions table
    op.create_table(
        'workflow_executions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workflow_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Drop all tables (baseline downgrade)."""
    op.drop_table('workflow_executions')
    op.drop_table('workflow_steps')
    op.drop_table('workflows')
    op.drop_table('webhook_events')
    op.drop_table('webhooks')
    op.drop_table('purchases')
    op.drop_table('customer_profiles')
    op.drop_table('audit_logs')
    op.drop_table('message_logs')
    op.drop_table('reputation_scores')
    op.drop_table('transactions')
    op.drop_table('org_balances')
    op.drop_table('ledger_entries')
    op.drop_table('ledger_accounts')
    op.drop_table('security_events')
    op.drop_table('coordinations')
    op.drop_table('api_keys')
    op.drop_table('agent_performance')
    op.drop_table('agent_capabilities')
    op.drop_table('agent_services')
    op.drop_table('agents')
    op.drop_index(op.f('ix_users_organization_id'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_agents_organization_id'), table_name='agents')
    op.drop_table('organizations')

