"""Add trust layer tables (Phase 7 PR-1)

Revision ID: i4j5k6l7m8n9
Revises: h3i4j5k6l7m8
Create Date: 2025-10-16 03:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'i4j5k6l7m8n9'
down_revision = 'h3i4j5k6l7m8'
branch_labels = None
depends_on = None


def upgrade():
    # Create reputation_snapshots table
    op.create_table(
        'reputation_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('subject_type', sa.String(10), nullable=False),
        sa.Column('subject_id', sa.String(36), nullable=False),
        sa.Column('score', sa.Integer, nullable=False),
        sa.Column('window', sa.String(10), nullable=False),
        sa.Column('reason', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("subject_type IN ('org', 'agent')", name='ck_reputation_subject_type'),
        sa.CheckConstraint("window IN ('7d', '30d', '90d')", name='ck_reputation_window'),
        sa.CheckConstraint('score >= 0 AND score <= 100', name='ck_reputation_score_range')
    )
    
    # Create indexes for reputation_snapshots
    op.create_index(
        'ix_reputation_snapshots_subject',
        'reputation_snapshots',
        ['subject_type', 'subject_id', 'created_at'],
        postgresql_ops={'created_at': 'DESC'}
    )
    
    # Create attestations table
    op.create_table(
        'attestations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('issuer_org', sa.String(36), nullable=False),
        sa.Column('subject_type', sa.String(10), nullable=False),
        sa.Column('subject_id', sa.String(36), nullable=False),
        sa.Column('scopes', postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column('weight', sa.Integer, nullable=False, server_default='1'),
        sa.Column('note', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("subject_type IN ('org', 'agent')", name='ck_attestation_subject_type'),
        sa.CheckConstraint('weight >= 1 AND weight <= 10', name='ck_attestation_weight_range')
    )
    
    # Create indexes for attestations
    op.create_index(
        'ix_attestations_issuer',
        'attestations',
        ['issuer_org', 'created_at'],
        postgresql_ops={'created_at': 'DESC'}
    )
    op.create_index(
        'ix_attestations_subject',
        'attestations',
        ['subject_type', 'subject_id']
    )
    
    # Create risk_events table
    op.create_table(
        'risk_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', sa.String(36), nullable=False),
        sa.Column('actor_id', sa.Text, nullable=True),
        sa.Column('type', sa.Text, nullable=False),
        sa.Column('severity', sa.String(10), nullable=False),
        sa.Column('meta', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("severity IN ('low', 'med', 'high')", name='ck_risk_event_severity')
    )
    
    # Create indexes for risk_events
    op.create_index(
        'ix_risk_events_org',
        'risk_events',
        ['org_id', 'created_at'],
        postgresql_ops={'created_at': 'DESC'}
    )
    op.create_index(
        'ix_risk_events_type',
        'risk_events',
        ['type', 'created_at'],
        postgresql_ops={'created_at': 'DESC'}
    )


def downgrade():
    # Drop indexes
    op.drop_index('ix_risk_events_type', table_name='risk_events')
    op.drop_index('ix_risk_events_org', table_name='risk_events')
    op.drop_index('ix_attestations_subject', table_name='attestations')
    op.drop_index('ix_attestations_issuer', table_name='attestations')
    op.drop_index('ix_reputation_snapshots_subject', table_name='reputation_snapshots')
    
    # Drop tables
    op.drop_table('risk_events')
    op.drop_table('attestations')
    op.drop_table('reputation_snapshots')

