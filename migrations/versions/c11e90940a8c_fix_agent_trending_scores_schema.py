"""fix_agent_trending_scores_schema

Revision ID: c11e90940a8c
Revises: 1e7218c37956
Create Date: 2025-10-17 01:17:35.460358

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c11e90940a8c'
down_revision: Union[str, Sequence[str], None] = '1e7218c37956'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix agent_trending_scores table schema"""
    
    # Rename 'score' column to 'trending_score'
    op.alter_column('agent_trending_scores', 'score',
                    new_column_name='trending_score',
                    existing_type=sa.Numeric(10, 4))
    
    # Add missing columns
    op.add_column('agent_trending_scores',
                  sa.Column('momentum', sa.Numeric(10, 4), server_default='0.0'))
    op.add_column('agent_trending_scores',
                  sa.Column('recent_installs', sa.Integer, server_default='0'))
    op.add_column('agent_trending_scores',
                  sa.Column('recent_views', sa.Integer, server_default='0'))
    op.add_column('agent_trending_scores',
                  sa.Column('recent_reviews', sa.Integer, server_default='0'))
    op.add_column('agent_trending_scores',
                  sa.Column('recent_usage', sa.Integer, server_default='0'))
    op.add_column('agent_trending_scores',
                  sa.Column('calculated_at', sa.DateTime, server_default=sa.func.now()))
    
    # Drop the 'rank' column as it's not in the model
    op.drop_column('agent_trending_scores', 'rank')
    
    # Add missing display_order column to agent_categories
    op.add_column('agent_categories',
                  sa.Column('display_order', sa.Integer, server_default='0'))


def downgrade() -> None:
    """Revert agent_trending_scores table schema changes"""
    
    # Add back 'rank' column
    op.add_column('agent_trending_scores',
                  sa.Column('rank', sa.Integer))
    
    # Remove added columns
    op.drop_column('agent_trending_scores', 'calculated_at')
    op.drop_column('agent_trending_scores', 'recent_usage')
    op.drop_column('agent_trending_scores', 'recent_reviews')
    op.drop_column('agent_trending_scores', 'recent_views')
    op.drop_column('agent_trending_scores', 'recent_installs')
    op.drop_column('agent_trending_scores', 'momentum')
    
    # Rename 'trending_score' back to 'score'
    op.alter_column('agent_trending_scores', 'trending_score',
                    new_column_name='score',
                    existing_type=sa.Numeric(10, 4))
    
    # Remove display_order from agent_categories
    op.drop_column('agent_categories', 'display_order')
