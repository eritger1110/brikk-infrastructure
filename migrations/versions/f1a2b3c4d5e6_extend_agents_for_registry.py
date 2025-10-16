"""extend_agents_for_registry

Revision ID: f1a2b3c4d5e6
Revises: e173b895ecb0
Create Date: 2025-10-15 23:10:00.000000

Extend agents table for Phase 6 Agent Registry requirements.
Adds category, oauth_client_id, active flag, and proper indexes for discovery.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e173b895ecb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns for Agent Registry
    op.add_column('agents', sa.Column('category', sa.Text(), nullable=True))
    op.add_column('agents', sa.Column('oauth_client_id', sa.Text(), nullable=True))
    op.add_column('agents', sa.Column('active', sa.Boolean(), nullable=False, server_default='true'))
    
    # Add foreign key constraint for oauth_client_id
    op.create_foreign_key(
        'fk_agents_oauth_client_id',
        'agents', 'oauth_clients',
        ['oauth_client_id'], ['client_id'],
        ondelete='SET NULL'
    )
    
    # Create indexes for discovery and filtering
    op.create_index('ix_agents_category', 'agents', ['category'])
    op.create_index('ix_agents_active', 'agents', ['active'])
    
    # Note: tags and capabilities already exist as TEXT columns in baseline schema
    # We'll handle JSON parsing in the model layer for backward compatibility


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_agents_active', table_name='agents')
    op.drop_index('ix_agents_category', table_name='agents')
    
    # Drop foreign key
    op.drop_constraint('fk_agents_oauth_client_id', 'agents', type_='foreignkey')
    
    # Drop columns
    op.drop_column('agents', 'active')
    op.drop_column('agents', 'oauth_client_id')
    op.drop_column('agents', 'category')

