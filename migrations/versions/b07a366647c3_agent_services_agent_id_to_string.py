"""agent_services_agent_id_to_string

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
    """Upgrade schema: Change agent_services.agent_id from Integer to String(36)."""
    # Drop existing FK constraint
    op.drop_constraint("agent_services_agent_id_fkey", "agent_services", type_="foreignkey")
    
    # Alter column type to String(36)
    op.alter_column(
        "agent_services",
        "agent_id",
        existing_type=sa.Integer(),
        type_=sa.String(length=36),
        nullable=False,
        postgresql_using="agent_id::text"  # Safe cast for existing rows
    )
    
    # Recreate FK to agents(id) with CASCADE
    op.create_foreign_key(
        "agent_services_agent_id_fkey",
        "agent_services",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="CASCADE"
    )


def downgrade() -> None:
    """Downgrade schema: Revert agent_services.agent_id to Integer."""
    # Drop the FK constraint
    op.drop_constraint("agent_services_agent_id_fkey", "agent_services", type_="foreignkey")
    
    # Revert column type to Integer
    op.alter_column(
        "agent_services",
        "agent_id",
        existing_type=sa.String(length=36),
        type_=sa.Integer(),
        nullable=False,
        postgresql_using="agent_id::integer"  # Cast back to integer
    )
    
    # Recreate the original FK
    op.create_foreign_key(
        "agent_services_agent_id_fkey",
        "agent_services",
        "agents",
        ["agent_id"],
        ["id"]
    )
