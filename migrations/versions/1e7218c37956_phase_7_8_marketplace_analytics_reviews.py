"""phase_7_8_marketplace_analytics_reviews

Revision ID: 1e7218c37956
Revises: p7_comprehensive
Create Date: 2025-10-17 01:04:35.986736

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1e7218c37956'
down_revision: Union[str, Sequence[str], None] = 'p7_comprehensive'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create Phase 7 & 8 tables"""
    
    # Marketplace: Categories
    op.create_table(
        'agent_categories',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('icon', sa.String(50)),
        sa.Column('parent_id', sa.String(36), sa.ForeignKey('agent_categories.id')),
        sa.Column('agent_count', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    
    # Marketplace: Tags
    op.create_table(
        'agent_tags',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('slug', sa.String(50), nullable=False, unique=True),
        sa.Column('usage_count', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    
    # Marketplace: Listings
    op.create_table(
        'marketplace_listings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('publisher_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='draft'),
        sa.Column('visibility', sa.String(20), nullable=False, default='public'),
        sa.Column('featured', sa.Boolean, default=False),
        sa.Column('featured_until', sa.DateTime),
        sa.Column('category', sa.String(100)),
        sa.Column('tags', postgresql.JSONB),
        sa.Column('short_description', sa.Text),
        sa.Column('long_description', sa.Text),
        sa.Column('icon_url', sa.Text),
        sa.Column('screenshots', postgresql.JSONB),
        sa.Column('demo_url', sa.Text),
        sa.Column('documentation_url', sa.Text),
        sa.Column('source_code_url', sa.Text),
        sa.Column('license', sa.String(50)),
        sa.Column('pricing_model', sa.String(20), default='free'),
        sa.Column('price_amount', sa.Numeric(10, 2)),
        sa.Column('price_currency', sa.String(3), default='USD'),
        sa.Column('install_count', sa.Integer, default=0),
        sa.Column('view_count', sa.Integer, default=0),
        sa.Column('published_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    
    # Marketplace: Installations
    op.create_table(
        'agent_installations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('org_id', sa.String(36)),
        sa.Column('status', sa.String(20), nullable=False, default='active'),
        sa.Column('installed_version', sa.String(50)),
        sa.Column('configuration', postgresql.JSONB),
        sa.Column('last_used_at', sa.DateTime),
        sa.Column('usage_count', sa.Integer, default=0),
        sa.Column('installed_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.UniqueConstraint('agent_id', 'user_id', name='uq_agent_user_installation'),
    )
    
    # Analytics: Usage Events
    op.create_table(
        'agent_usage_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('user_id', sa.String(36)),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('duration_ms', sa.Integer),
        sa.Column('success', sa.Boolean),
        sa.Column('error_message', sa.Text),
        sa.Column('event_metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_agent_usage_events_created_at', 'agent_usage_events', ['created_at'])
    
    # Analytics: Daily Agent Analytics
    op.create_table(
        'agent_analytics_daily',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('invocation_count', sa.Integer, default=0),
        sa.Column('unique_users', sa.Integer, default=0),
        sa.Column('success_count', sa.Integer, default=0),
        sa.Column('error_count', sa.Integer, default=0),
        sa.Column('avg_duration_ms', sa.Numeric(10, 2)),
        sa.Column('p50_duration_ms', sa.Integer),
        sa.Column('p95_duration_ms', sa.Integer),
        sa.Column('p99_duration_ms', sa.Integer),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.UniqueConstraint('agent_id', 'date', name='uq_agent_analytics_daily'),
    )
    
    # Analytics: Daily User Analytics
    op.create_table(
        'user_analytics_daily',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('agents_used', sa.Integer, default=0),
        sa.Column('total_invocations', sa.Integer, default=0),
        sa.Column('unique_agents', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.UniqueConstraint('user_id', 'date', name='uq_user_analytics_daily'),
    )
    
    # Analytics: Trending Scores
    op.create_table(
        'agent_trending_scores',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id'), nullable=False, unique=True),
        sa.Column('score', sa.Numeric(10, 4), default=0),
        sa.Column('rank', sa.Integer),
        sa.Column('velocity', sa.Numeric(10, 4), default=0),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    
    # Reviews: Agent Reviews
    op.create_table(
        'agent_reviews',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('rating', sa.Integer, nullable=False),
        sa.Column('title', sa.String(200)),
        sa.Column('review_text', sa.Text),
        sa.Column('verified_user', sa.Boolean, default=False),
        sa.Column('helpful_count', sa.Integer, default=0),
        sa.Column('unhelpful_count', sa.Integer, default=0),
        sa.Column('flagged', sa.Boolean, default=False),
        sa.Column('flag_reason', sa.Text),
        sa.Column('publisher_response', sa.Text),
        sa.Column('publisher_response_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.UniqueConstraint('agent_id', 'user_id', name='uq_agent_user_review'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
    )
    
    # Reviews: Review Votes
    op.create_table(
        'review_votes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('review_id', sa.String(36), sa.ForeignKey('agent_reviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('vote_type', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.UniqueConstraint('review_id', 'user_id', name='uq_review_user_vote'),
        sa.CheckConstraint("vote_type IN ('helpful', 'unhelpful')", name='check_vote_type'),
    )
    
    # Reviews: Rating Summaries
    op.create_table(
        'agent_rating_summaries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agents.id'), nullable=False, unique=True),
        sa.Column('total_reviews', sa.Integer, default=0),
        sa.Column('average_rating', sa.Numeric(3, 2), default=0),
        sa.Column('rating_1_count', sa.Integer, default=0),
        sa.Column('rating_2_count', sa.Integer, default=0),
        sa.Column('rating_3_count', sa.Integer, default=0),
        sa.Column('rating_4_count', sa.Integer, default=0),
        sa.Column('rating_5_count', sa.Integer, default=0),
        sa.Column('verified_reviews_count', sa.Integer, default=0),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema - Drop Phase 7 & 8 tables"""
    op.drop_table('agent_rating_summaries')
    op.drop_table('review_votes')
    op.drop_table('agent_reviews')
    op.drop_table('agent_trending_scores')
    op.drop_table('user_analytics_daily')
    op.drop_table('agent_analytics_daily')
    op.drop_index('ix_agent_usage_events_created_at')
    op.drop_table('agent_usage_events')
    op.drop_table('agent_installations')
    op.drop_table('marketplace_listings')
    op.drop_table('agent_tags')
    op.drop_table('agent_categories')

