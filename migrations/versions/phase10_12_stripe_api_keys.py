"""Add Stripe fields to ApiKey model

Revision ID: phase10_12_stripe_api_keys
Revises: p7_comprehensive
Create Date: 2025-10-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'phase10_12_stripe_api_keys'
down_revision = 'beta_applications'
branch_labels = None
depends_on = None


def upgrade():
    # Add user_id column to api_keys table
    op.add_column('api_keys', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_api_keys_user_id'), 'api_keys', ['user_id'], unique=False)
    op.create_foreign_key('fk_api_keys_user_id', 'api_keys', 'users', ['user_id'], ['id'])
    
    # Add Stripe integration columns
    op.add_column('api_keys', sa.Column('stripe_subscription_id', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_api_keys_stripe_subscription_id'), 'api_keys', ['stripe_subscription_id'], unique=False)
    
    op.add_column('api_keys', sa.Column('tier', sa.String(length=32), nullable=False, server_default='free'))
    
    # Make organization_id nullable (for individual user subscriptions)
    op.alter_column('api_keys', 'organization_id',
               existing_type=sa.INTEGER(),
               nullable=True)


def downgrade():
    # Remove Stripe columns
    op.drop_column('api_keys', 'tier')
    op.drop_index(op.f('ix_api_keys_stripe_subscription_id'), table_name='api_keys')
    op.drop_column('api_keys', 'stripe_subscription_id')
    
    # Remove user_id
    op.drop_constraint('fk_api_keys_user_id', 'api_keys', type_='foreignkey')
    op.drop_index(op.f('ix_api_keys_user_id'), table_name='api_keys')
    op.drop_column('api_keys', 'user_id')
    
    # Make organization_id non-nullable again
    op.alter_column('api_keys', 'organization_id',
               existing_type=sa.INTEGER(),
               nullable=False)

