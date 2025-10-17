#!/usr/bin/env python3.11
"""
Fix Alembic version table by removing references to deleted migrations.

This script connects to the database and updates the alembic_version table
to point to the correct migration head.
"""
import os
import sys
from sqlalchemy import create_engine, text

def fix_alembic_version():
    """Fix the alembic_version table."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Convert postgres:// to postgresql:// if needed
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Check current version
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        current_version = result.scalar()
        print(f"Current alembic version: {current_version}")
        
        # If it's one of the deleted migrations, update to p7_comprehensive
        deleted_migrations = ['1e7218c37956', 'c11e90940a8c', 'f3bf1d525d95']
        
        if current_version in deleted_migrations:
            print(f"Detected deleted migration {current_version}, fixing...")
            conn.execute(text("UPDATE alembic_version SET version_num = 'p7_comprehensive'"))
            conn.commit()
            print("✓ Updated alembic_version to p7_comprehensive")
        else:
            print(f"✓ Version {current_version} is valid, no fix needed")

if __name__ == '__main__':
    fix_alembic_version()

