"""Dashboard Auth0 integration

Revision ID: dashboard_auth0
Revises: p7_comprehensive_trust_layer
Create Date: 2025-11-13 18:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dashboard_auth0'
down_revision = 'p7_comprehensive_trust_layer'
branch_labels = None
depends_on = None


def upgrade():
    # Add Auth0 fields to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('auth0_user_id', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('picture', sa.String(length=512), nullable=True))
        batch_op.create_index('ix_users_auth0_user_id', ['auth0_user_id'], unique=True)

    # Add Stripe and subscription fields to organizations table
    with op.batch_alter_table('organizations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('stripe_customer_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('stripe_subscription_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('plan_tier', sa.String(length=50), nullable=False, server_default='FREE'))
        batch_op.add_column(sa.Column('subscription_status', sa.String(length=50), nullable=False, server_default='active'))
        batch_op.add_column(sa.Column('current_period_end', sa.DateTime(), nullable=True))
        batch_op.create_index('ix_organizations_stripe_customer_id', ['stripe_customer_id'], unique=True)
        batch_op.create_index('ix_organizations_stripe_subscription_id', ['stripe_subscription_id'], unique=False)


def downgrade():
    # Remove indexes and columns from organizations table
    with op.batch_alter_table('organizations', schema=None) as batch_op:
        batch_op.drop_index('ix_organizations_stripe_subscription_id')
        batch_op.drop_index('ix_organizations_stripe_customer_id')
        batch_op.drop_column('current_period_end')
        batch_op.drop_column('subscription_status')
        batch_op.drop_column('plan_tier')
        batch_op.drop_column('stripe_subscription_id')
        batch_op.drop_column('stripe_customer_id')

    # Remove indexes and columns from users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('ix_users_auth0_user_id')
        batch_op.drop_column('picture')
        batch_op.drop_column('name')
        batch_op.drop_column('auth0_user_id')
