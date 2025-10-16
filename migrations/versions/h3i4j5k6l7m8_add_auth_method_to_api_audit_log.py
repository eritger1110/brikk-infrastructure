"""add auth_method to api_audit_log

Revision ID: h3i4j5k6l7m8
Revises: g2h3i4j5k6l7
Create Date: 2025-10-16 01:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'h3i4j5k6l7m8'
down_revision = 'g2h3i4j5k6l7'
branch_labels = None
depends_on = None


def upgrade():
    # Add auth_method column with default value
    op.add_column(
        'api_audit_log',
        sa.Column('auth_method', sa.String(length=16), nullable=False, server_default='api_key')
    )
    
    # Backfill existing rows from actor_type if needed
    op.execute("""
        UPDATE api_audit_log 
        SET auth_method = actor_type 
        WHERE auth_method = 'api_key'
    """)


def downgrade():
    op.drop_column('api_audit_log', 'auth_method')

