"""Phase 7: Comprehensive trust layer - reputation, risk, attestations

Revision ID: p7_comprehensive
Revises: h3i4j5k6l7m8
Create Date: 2025-10-16 03:52:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'p7_comprehensive'
down_revision = 'h3i4j5k6l7m8'
branch_labels = None
depends_on = None


def upgrade():
    # Reputation snapshots table
    op.create_table('reputation_snapshots',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('subject_type', sa.String(length=20), nullable=False),
        sa.Column('subject_id', sa.String(length=36), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('window_days', sa.Integer(), nullable=False),
        sa.Column('components', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('score >= 0 AND score <= 100', name='ck_reputation_score_range'),
        sa.CheckConstraint("subject_type IN ('org', 'agent')", name='ck_reputation_subject_type'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reputation_subject', 'reputation_snapshots', ['subject_type', 'subject_id', 'window_days'], unique=False)
    op.create_index('ix_reputation_created', 'reputation_snapshots', ['created_at'], unique=False)

    # Attestations table
    op.create_table('attestations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('issuer_org_id', sa.Integer(), nullable=False),
        sa.Column('subject_type', sa.String(length=20), nullable=False),
        sa.Column('subject_id', sa.String(length=36), nullable=False),
        sa.Column('claim', sa.Text(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('revoked', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('score >= 0 AND score <= 100', name='ck_attestation_score_range'),
        sa.CheckConstraint("subject_type IN ('org', 'agent')", name='ck_attestation_subject_type'),
        sa.ForeignKeyConstraint(['issuer_org_id'], ['organizations.id'], name='fk_attestation_issuer_org'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_attestation_subject', 'attestations', ['subject_type', 'subject_id'], unique=False)
    op.create_index('ix_attestation_issuer', 'attestations', ['issuer_org_id'], unique=False)

    # Risk events table
    op.create_table('risk_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=10), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high')", name='ck_risk_severity'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], name='fk_risk_event_org'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_risk_org_created', 'risk_events', ['org_id', 'created_at'], unique=False)


def downgrade():
    op.drop_index('ix_risk_org_created', table_name='risk_events')
    op.drop_table('risk_events')
    op.drop_index('ix_attestation_issuer', table_name='attestations')
    op.drop_index('ix_attestation_subject', table_name='attestations')
    op.drop_table('attestations')
    op.drop_index('ix_reputation_created', table_name='reputation_snapshots')
    op.drop_index('ix_reputation_subject', table_name='reputation_snapshots')
    op.drop_table('reputation_snapshots')

