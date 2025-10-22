#!/usr/bin/env python3.11
"""
Create Phase 7 & 8 database tables

This script creates the marketplace, analytics, and reviews tables
that were added in Phase 7 & 8 but don't have Alembic migrations yet.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infra.db import db
from src.factory import create_app

# Import all Phase 7 & 8 models to ensure they're registered
from src.models.marketplace import MarketplaceListing, AgentCategory, AgentTag, AgentInstallation
from src.models.analytics import AgentUsageEvent, AgentAnalyticsDaily, UserAnalyticsDaily, AgentTrendingScore
from src.models.reviews import AgentReview, ReviewVote, AgentRatingSummary


def main():
    """Create Phase 7 & 8 tables"""
    print("Creating Phase 7 & 8 database tables...")
    
    # Create Flask app with database connection
    app = create_app()
    
    with app.app_context():
        # Get list of existing tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        print(f"Found {len(existing_tables)} existing tables")
        
        # Tables we want to create
        phase_7_8_tables = [
            'marketplace_listings',
            'agent_categories',
            'agent_tags',
            'agent_installations',
            'agent_usage_events',
            'agent_analytics_daily',
            'user_analytics_daily',
            'agent_trending_scores',
            'agent_reviews',
            'review_votes',
            'agent_rating_summaries',
        ]
        
        # Check which tables are missing
        missing_tables = [t for t in phase_7_8_tables if t not in existing_tables]
        
        if not missing_tables:
            print("[OK] All Phase 7 & 8 tables already exist!")
            return 0
        
        print(f"Creating {len(missing_tables)} missing tables:")
        for table in missing_tables:
            print(f"  - {table}")
        
        # Create only the missing tables
        # We use create_all() with checkfirst=True to avoid errors
        db.create_all()
        
        print("[OK] Phase 7 & 8 tables created successfully!")
        
        # Verify tables were created
        inspector = inspect(db.engine)
        new_existing_tables = inspector.get_table_names()
        newly_created = set(new_existing_tables) - set(existing_tables)
        
        if newly_created:
            print(f"\nNewly created tables ({len(newly_created)}):")
            for table in sorted(newly_created):
                print(f"  [OK] {table}")
        
        return 0


if __name__ == '__main__':
    sys.exit(main())

