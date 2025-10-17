"""phase_7_8_schema_with_alter_table

Revision ID: 5c0a0aab7b03
Revises: p7_comprehensive
Create Date: 2025-10-17 12:05:35.432511

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c0a0aab7b03'
down_revision: Union[str, Sequence[str], None] = 'p7_comprehensive'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Smart migration that handles both new table creation and adding missing columns.
    Uses PostgreSQL-specific syntax for conditional column addition.
    """
    
    # For marketplace_listings, add missing columns if they don't exist
    op.execute("""
        DO $$ 
        BEGIN
            -- Add is_featured column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='marketplace_listings' AND column_name='is_featured') THEN
                ALTER TABLE marketplace_listings ADD COLUMN is_featured BOOLEAN DEFAULT FALSE;
            END IF;
            
            -- Add is_verified column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='marketplace_listings' AND column_name='is_verified') THEN
                ALTER TABLE marketplace_listings ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;
            END IF;
            
            -- Add long_description column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='marketplace_listings' AND column_name='long_description') THEN
                ALTER TABLE marketplace_listings ADD COLUMN long_description TEXT;
            END IF;
            
            -- Add author_url column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='marketplace_listings' AND column_name='author_url') THEN
                ALTER TABLE marketplace_listings ADD COLUMN author_url VARCHAR(500);
            END IF;
            
            -- Add documentation_url column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='marketplace_listings' AND column_name='documentation_url') THEN
                ALTER TABLE marketplace_listings ADD COLUMN documentation_url VARCHAR(500);
            END IF;
            
            -- Add source_url column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='marketplace_listings' AND column_name='source_url') THEN
                ALTER TABLE marketplace_listings ADD COLUMN source_url VARCHAR(500);
            END IF;
            
            -- Add license column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='marketplace_listings' AND column_name='license') THEN
                ALTER TABLE marketplace_listings ADD COLUMN license VARCHAR(100);
            END IF;
            
            -- Add pricing_model column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='marketplace_listings' AND column_name='pricing_model') THEN
                ALTER TABLE marketplace_listings ADD COLUMN pricing_model VARCHAR(50);
            END IF;
            
            -- Add base_price column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='marketplace_listings' AND column_name='base_price') THEN
                ALTER TABLE marketplace_listings ADD COLUMN base_price DECIMAL(10, 2);
            END IF;
            
            -- Add published_at column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='marketplace_listings' AND column_name='published_at') THEN
                ALTER TABLE marketplace_listings ADD COLUMN published_at TIMESTAMP;
            END IF;
        END $$;
    """)
    
    # Add indexes if they don't exist
    op.execute("CREATE INDEX IF NOT EXISTS ix_marketplace_listings_is_featured ON marketplace_listings(is_featured);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_marketplace_listings_is_verified ON marketplace_listings(is_verified);")
    
    # For agent_categories, add display_order if it doesn't exist
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='agent_categories' AND column_name='display_order') THEN
                ALTER TABLE agent_categories ADD COLUMN display_order INTEGER DEFAULT 0;
            END IF;
        END $$;
    """)
    
    # For agent_trending_scores, ensure all columns exist
    op.execute("""
        DO $$ 
        BEGIN
            -- Add trending_score column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='agent_trending_scores' AND column_name='trending_score') THEN
                ALTER TABLE agent_trending_scores ADD COLUMN trending_score DECIMAL(10, 4) NOT NULL DEFAULT 0.0;
            END IF;
            
            -- Add momentum column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='agent_trending_scores' AND column_name='momentum') THEN
                ALTER TABLE agent_trending_scores ADD COLUMN momentum DECIMAL(10, 4) DEFAULT 0.0;
            END IF;
            
            -- Add recent_installs column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='agent_trending_scores' AND column_name='recent_installs') THEN
                ALTER TABLE agent_trending_scores ADD COLUMN recent_installs INTEGER DEFAULT 0;
            END IF;
            
            -- Add recent_views column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='agent_trending_scores' AND column_name='recent_views') THEN
                ALTER TABLE agent_trending_scores ADD COLUMN recent_views INTEGER DEFAULT 0;
            END IF;
            
            -- Add recent_reviews column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='agent_trending_scores' AND column_name='recent_reviews') THEN
                ALTER TABLE agent_trending_scores ADD COLUMN recent_reviews INTEGER DEFAULT 0;
            END IF;
            
            -- Add recent_usage column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='agent_trending_scores' AND column_name='recent_usage') THEN
                ALTER TABLE agent_trending_scores ADD COLUMN recent_usage INTEGER DEFAULT 0;
            END IF;
            
            -- Add calculated_at column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name='agent_trending_scores' AND column_name='calculated_at') THEN
                ALTER TABLE agent_trending_scores ADD COLUMN calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            END IF;
            
            -- Remove old 'score' column if it exists
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='agent_trending_scores' AND column_name='score') THEN
                ALTER TABLE agent_trending_scores DROP COLUMN score;
            END IF;
            
            -- Remove old 'rank' column if it exists
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name='agent_trending_scores' AND column_name='rank') THEN
                ALTER TABLE agent_trending_scores DROP COLUMN rank;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    pass
