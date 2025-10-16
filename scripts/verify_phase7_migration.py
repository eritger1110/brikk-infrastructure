#!/usr/bin/env python3
"""
Phase 7 Migration Verification Script
Verifies that all Phase 7 tables exist and have correct schema
"""

import os
import sys
from sqlalchemy import create_engine, inspect, text

# Expected Phase 7 tables
EXPECTED_TABLES = [
    'marketplace_listings',
    'marketplace_categories',
    'marketplace_tags',
    'agent_installations',
    'agent_usage_events',
    'agent_daily_stats',
    'agent_trending_scores',
    'agent_reviews',
    'review_votes',
    'agent_rating_summaries',
    'publisher_review_responses',
]

def verify_migration():
    """Verify Phase 7 migration was successful"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("[ERROR] DATABASE_URL environment variable not set")
        return False
    
    try:
        # Create engine
        engine = create_engine(database_url)
        inspector = inspect(engine)
        
        # Get existing tables
        existing_tables = inspector.get_table_names()
        
        print("=" * 60)
        print("Phase 7 Migration Verification")
        print("=" * 60)
        
        # Check each expected table
        missing_tables = []
        for table in EXPECTED_TABLES:
            if table in existing_tables:
                # Get column count
                columns = inspector.get_columns(table)
                print(f"[OK] {table} ({len(columns)} columns)")
            else:
                print(f"[MISSING] {table}")
                missing_tables.append(table)
        
        print("=" * 60)
        
        if missing_tables:
            print(f"[ERROR] {len(missing_tables)} tables missing:")
            for table in missing_tables:
                print(f"  - {table}")
            return False
        
        # Verify seed data
        print("\nVerifying seed data...")
        with engine.connect() as conn:
            # Check categories
            result = conn.execute(text("SELECT COUNT(*) FROM marketplace_categories"))
            category_count = result.scalar()
            print(f"[INFO] marketplace_categories: {category_count} rows")
            
            # Check tags
            result = conn.execute(text("SELECT COUNT(*) FROM marketplace_tags"))
            tag_count = result.scalar()
            print(f"[INFO] marketplace_tags: {tag_count} rows")
        
        print("\n" + "=" * 60)
        print("[SUCCESS] All Phase 7 tables exist and are populated!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"[ERROR] Migration verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = verify_migration()
    sys.exit(0 if success else 1)

