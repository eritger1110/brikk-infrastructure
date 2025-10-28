"""Fix api_keys schema - add missing columns

Revision ID: fix_api_keys_schema
Revises: phase10_12_stripe_api_keys
Create Date: 2025-10-28 18:00:00.000000

This migration ensures all required columns exist in the api_keys table.
Safe to run multiple times - checks for column existence before adding.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'fix_api_keys_schema'
down_revision = 'phase10_12_stripe_api_keys'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade():
    """Add missing columns to api_keys table if they don't exist."""
    
    # Add api_key_encrypted if missing (required for Fernet encryption)
    if not column_exists('api_keys', 'api_key_encrypted'):
        print("Adding api_key_encrypted column...")
        op.add_column('api_keys', sa.Column('api_key_encrypted', sa.Text(), nullable=True))
        # We'll set nullable=True initially, then update existing rows
    
    # Add key_id if missing
    if not column_exists('api_keys', 'key_id'):
        print("Adding key_id column...")
        op.add_column('api_keys', sa.Column('key_id', sa.String(length=64), nullable=True))
        op.create_index(op.f('ix_api_keys_key_id'), 'api_keys', ['key_id'], unique=True)
    
    # Add key_prefix if missing
    if not column_exists('api_keys', 'key_prefix'):
        print("Adding key_prefix column...")
        op.add_column('api_keys', sa.Column('key_prefix', sa.String(length=16), nullable=True))
        op.create_index(op.f('ix_api_keys_key_prefix'), 'api_keys', ['key_prefix'], unique=False)
    
    # Add soft_cap_usd if missing
    if not column_exists('api_keys', 'soft_cap_usd'):
        print("Adding soft_cap_usd column...")
        op.add_column('api_keys', sa.Column('soft_cap_usd', sa.Numeric(10, 4), server_default='5.00'))
    
    # Add hard_cap_usd if missing
    if not column_exists('api_keys', 'hard_cap_usd'):
        print("Adding hard_cap_usd column...")
        op.add_column('api_keys', sa.Column('hard_cap_usd', sa.Numeric(10, 4), server_default='10.00'))
    
    # Add last_failure_at if missing
    if not column_exists('api_keys', 'last_failure_at'):
        print("Adding last_failure_at column...")
        op.add_column('api_keys', sa.Column('last_failure_at', sa.DateTime(), nullable=True))
    
    # Add requests_per_minute if missing
    if not column_exists('api_keys', 'requests_per_minute'):
        print("Adding requests_per_minute column...")
        op.add_column('api_keys', sa.Column('requests_per_minute', sa.Integer(), server_default='100'))
    
    # Add requests_per_hour if missing
    if not column_exists('api_keys', 'requests_per_hour'):
        print("Adding requests_per_hour column...")
        op.add_column('api_keys', sa.Column('requests_per_hour', sa.Integer(), server_default='1000'))
    
    print("Schema migration completed successfully!")


def downgrade():
    """Remove columns added in upgrade (only if safe to do so)."""
    # Note: We don't drop columns in downgrade to prevent data loss
    # If you need to rollback, do it manually
    pass

