"""add_api_gateway_tables

Revision ID: e173b895ecb0
Revises: b07a366647c3
Create Date: 2025-10-15 14:54:02.023229

API Gateway tables for OAuth2, API keys, and audit logging.

Tables added:
- org_api_keys: Scoped API keys for organizations
- oauth_clients: OAuth2 client registrations
- oauth_tokens: OAuth2 access/refresh tokens
- api_audit_log: Audit trail for API requests

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e173b895ecb0'
down_revision: Union[str, Sequence[str], None] = 'b07a366647c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add API Gateway tables."""
    
    # --- org_api_keys ---
    op.create_table(
        "org_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.String()), nullable=False, 
                  server_default="{}"),
        sa.Column("tier", sa.String(32), nullable=False, server_default="FREE"),
        sa.Column("created_at", sa.DateTime(timezone=False), 
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=False), nullable=True),
    )
    op.create_index("ix_org_api_keys_org_id", "org_api_keys", ["org_id"])
    op.create_index("ix_org_api_keys_revoked_at", "org_api_keys", ["revoked_at"])
    op.create_index("ix_org_api_keys_scopes", "org_api_keys", ["scopes"], 
                    postgresql_using="gin")

    # --- oauth_clients ---
    op.create_table(
        "oauth_clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", sa.String(80), nullable=False, unique=True),
        sa.Column("client_secret_hash", sa.String(255), nullable=False),
        sa.Column("grant_types", postgresql.ARRAY(sa.String()), nullable=False, 
                  server_default=sa.text("ARRAY['client_credentials']::text[]")),
        sa.Column("redirect_uris", postgresql.ARRAY(sa.String()), nullable=False, 
                  server_default="{}"),
        sa.Column("scopes", postgresql.ARRAY(sa.String()), nullable=False, 
                  server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=False), 
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=False), nullable=True),
    )
    op.create_index("ix_oauth_clients_org", "oauth_clients", ["org_id"])

    # --- oauth_tokens ---
    op.create_table(
        "oauth_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", sa.String(80), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject", sa.String(120), nullable=True),
        sa.Column("scopes", postgresql.ARRAY(sa.String()), nullable=False, 
                  server_default="{}"),
        sa.Column("token_type", sa.String(16), nullable=False, server_default="access"),
        sa.Column("issued_at", sa.DateTime(timezone=False), 
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=False), nullable=True),
    )
    op.create_index("ix_oauth_tokens_client", "oauth_tokens", ["client_id"])
    op.create_index("ix_oauth_tokens_org", "oauth_tokens", ["org_id"])
    op.create_index("ix_oauth_tokens_exp", "oauth_tokens", ["expires_at"])

    # --- api_audit_log ---
    op.create_table(
        "api_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, 
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(16), nullable=False),  # api_key|oauth|hmac
        sa.Column("actor_id", sa.String(120), nullable=False),   # key id or client_id
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("method", sa.String(8), nullable=False),
        sa.Column("path", sa.String(256), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("cost_units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), 
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_api_audit_log_org_created", "api_audit_log", 
                    ["org_id", "created_at"])
    op.create_index("ix_api_audit_log_actor_created", "api_audit_log", 
                    ["actor_id", "created_at"])


def downgrade() -> None:
    """Downgrade schema - remove API Gateway tables."""
    
    # Drop in reverse order
    op.drop_index("ix_api_audit_log_actor_created", table_name="api_audit_log")
    op.drop_index("ix_api_audit_log_org_created", table_name="api_audit_log")
    op.drop_table("api_audit_log")

    op.drop_index("ix_oauth_tokens_exp", table_name="oauth_tokens")
    op.drop_index("ix_oauth_tokens_org", table_name="oauth_tokens")
    op.drop_index("ix_oauth_tokens_client", table_name="oauth_tokens")
    op.drop_table("oauth_tokens")

    op.drop_index("ix_oauth_clients_org", table_name="oauth_clients")
    op.drop_table("oauth_clients")

    op.drop_index("ix_org_api_keys_scopes", table_name="org_api_keys")
    op.drop_index("ix_org_api_keys_revoked_at", table_name="org_api_keys")
    op.drop_index("ix_org_api_keys_org_id", table_name="org_api_keys")
    op.drop_table("org_api_keys")

