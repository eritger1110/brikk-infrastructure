"""rename_score_to_trending_score

Revision ID: f3bf1d525d95
Revises: c11e90940a8c
Create Date: 2025-10-17 01:22:29.404239

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3bf1d525d95'
down_revision: Union[str, Sequence[str], None] = 'c11e90940a8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename score column to trending_score using raw SQL"""
    
    # Use raw SQL to rename the column
    op.execute('ALTER TABLE agent_trending_scores RENAME COLUMN score TO trending_score')


def downgrade() -> None:
    """Rename trending_score back to score"""
    
    op.execute('ALTER TABLE agent_trending_scores RENAME COLUMN trending_score TO score')
