"""phase_7_8_complete_schema

Revision ID: 0d268fd58db2
Revises: p7_comprehensive
Create Date: 2025-10-17 02:13:57.180716

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d268fd58db2'
down_revision: Union[str, Sequence[str], None] = 'p7_comprehensive'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Use raw SQL with IF NOT EXISTS to avoid conflicts
    op.execute("""
        CREATE TABLE IF NOT EXISTS marketplace_listings (
            id VARCHAR(36) PRIMARY KEY,
            agent_id VARCHAR(36) NOT NULL,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            long_description TEXT,
            category VARCHAR(100),
            tags VARCHAR(255),
            version VARCHAR(50),
            author VARCHAR(200),
            author_url VARCHAR(500),
            documentation_url VARCHAR(500),
            source_url VARCHAR(500),
            license VARCHAR(100),
            pricing_model VARCHAR(50),
            base_price DECIMAL(10, 2),
            install_count INTEGER DEFAULT 0,
            rating DECIMAL(3, 2),
            review_count INTEGER DEFAULT 0,
            is_featured BOOLEAN DEFAULT FALSE,
            is_verified BOOLEAN DEFAULT FALSE,
            status VARCHAR(50) DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            published_at TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS ix_marketplace_listings_agent_id ON marketplace_listings(agent_id);
        CREATE INDEX IF NOT EXISTS ix_marketplace_listings_category ON marketplace_listings(category);
        CREATE INDEX IF NOT EXISTS ix_marketplace_listings_status ON marketplace_listings(status);
        CREATE INDEX IF NOT EXISTS ix_marketplace_listings_is_featured ON marketplace_listings(is_featured);
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_categories (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            icon VARCHAR(100),
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_tags (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_reviews (
            id VARCHAR(36) PRIMARY KEY,
            agent_id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36) NOT NULL,
            rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
            title VARCHAR(200),
            comment TEXT,
            helpful_count INTEGER DEFAULT 0,
            verified_purchase BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS ix_agent_reviews_agent_id ON agent_reviews(agent_id);
        CREATE INDEX IF NOT EXISTS ix_agent_reviews_user_id ON agent_reviews(user_id);
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_analytics_events (
            id VARCHAR(36) PRIMARY KEY,
            agent_id VARCHAR(36) NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            user_id VARCHAR(36),
            session_id VARCHAR(100),
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS ix_agent_analytics_events_agent_id ON agent_analytics_events(agent_id);
        CREATE INDEX IF NOT EXISTS ix_agent_analytics_events_event_type ON agent_analytics_events(event_type);
        CREATE INDEX IF NOT EXISTS ix_agent_analytics_events_created_at ON agent_analytics_events(created_at);
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_trending_scores (
            id VARCHAR(36) PRIMARY KEY,
            agent_id VARCHAR(36) UNIQUE NOT NULL,
            trending_score DECIMAL(10, 4) DEFAULT 0.0,
            momentum DECIMAL(10, 4) DEFAULT 0.0,
            recent_installs INTEGER DEFAULT 0,
            recent_views INTEGER DEFAULT 0,
            recent_reviews INTEGER DEFAULT 0,
            recent_usage INTEGER DEFAULT 0,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS ix_agent_trending_scores_agent_id ON agent_trending_scores(agent_id);
        CREATE INDEX IF NOT EXISTS ix_agent_trending_scores_trending_score ON agent_trending_scores(trending_score DESC);
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS agent_trending_scores CASCADE;")
    op.execute("DROP TABLE IF EXISTS agent_analytics_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS agent_reviews CASCADE;")
    op.execute("DROP TABLE IF EXISTS agent_tags CASCADE;")
    op.execute("DROP TABLE IF EXISTS agent_categories CASCADE;")
    op.execute("DROP TABLE IF EXISTS marketplace_listings CASCADE;")
