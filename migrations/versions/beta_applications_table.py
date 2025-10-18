"""add_beta_applications_table

Revision ID: beta_applications
Revises: 5c0a0aab7b03
Create Date: 2025-01-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'beta_applications'
down_revision = '5c0a0aab7b03'
branch_labels = None
depends_on = None


def upgrade():
    # Create beta_applications table
    op.execute("""
        CREATE TABLE IF NOT EXISTS beta_applications (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            company VARCHAR(255),
            use_case TEXT NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            source VARCHAR(100),
            ip_address VARCHAR(45),
            user_agent VARCHAR(500),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP,
            invited_at TIMESTAMP,
            admin_notes TEXT,
            reviewed_by VARCHAR(255),
            api_key VARCHAR(64) UNIQUE
        );
    """)
    
    # Create indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_beta_applications_email ON beta_applications(email);
        CREATE INDEX IF NOT EXISTS ix_beta_applications_status ON beta_applications(status);
        CREATE INDEX IF NOT EXISTS ix_beta_applications_created_at ON beta_applications(created_at);
        CREATE INDEX IF NOT EXISTS ix_beta_applications_api_key ON beta_applications(api_key);
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS beta_applications CASCADE;")

