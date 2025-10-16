"""add_usage_ledger

Revision ID: g2h3i4j5k6l7
Revises: f1a2b3c4d5e6
Create Date: 2025-10-15 23:30:00.000000

Add usage_ledger table for metered billing (Phase 6 PR-2).
Tracks API usage per organization with cost calculation for Stripe sync.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'g2h3i4j5k6l7'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create usage_ledger table
    op.create_table(
        'usage_ledger',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', sa.String(36), nullable=False, index=True),  # String to match existing orgs table
        sa.Column('actor_id', sa.Text(), nullable=False),  # API key or OAuth client ID
        sa.Column('agent_id', sa.String(36), nullable=True, index=True),  # Optional, String to match agents table
        sa.Column('route', sa.Text(), nullable=False),
        sa.Column('usage_units', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_cost', sa.Numeric(10, 4), nullable=False),
        sa.Column('total_cost', sa.Numeric(10, 4), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('billed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for efficient querying
    op.create_index('ix_usage_ledger_org_id', 'usage_ledger', ['org_id'])
    op.create_index('ix_usage_ledger_agent_id', 'usage_ledger', ['agent_id'])
    op.create_index('ix_usage_ledger_created_at', 'usage_ledger', ['created_at'])
    op.create_index('ix_usage_ledger_billed_at', 'usage_ledger', ['billed_at'])
    
    # Composite index for unbilled queries
    op.create_index('ix_usage_ledger_unbilled', 'usage_ledger', ['org_id', 'created_at'], 
                    postgresql_where=sa.text('billed_at IS NULL'))


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_usage_ledger_unbilled', table_name='usage_ledger')
    op.drop_index('ix_usage_ledger_billed_at', table_name='usage_ledger')
    op.drop_index('ix_usage_ledger_created_at', table_name='usage_ledger')
    op.drop_index('ix_usage_ledger_agent_id', table_name='usage_ledger')
    op.drop_index('ix_usage_ledger_org_id', table_name='usage_ledger')
    
    # Drop table
    op.drop_table('usage_ledger')

