#!/usr/bin/env python3
"""
Deploy Seed Agents to Marketplace
Registers the seed agents (CSV Analyzer, Email Summarizer, Code Reviewer) in the marketplace
"""

import os
import sys
import json
import requests
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infra.db import db
from src.models.agent import Agent
from src.models.marketplace import MarketplaceListing
from src.factory import create_app

# Seed agent configurations
SEED_AGENTS = [
    {
        "agent_id": "csv-analyzer",
        "name": "CSV Analyzer",
        "description": "Parse and analyze CSV files with automatic type detection and statistical insights",
        "category": "Data & Analytics",
        "tags": ["csv", "data-analysis", "statistics", "analytics"],
        "endpoint_url": "https://seed-agents.brikk.ai/csv-analyzer",
        "version": "1.0.0",
        "pricing_model": "free",
        "is_verified": True,
        "is_featured": True
    },
    {
        "agent_id": "email-summarizer",
        "name": "Email Summarizer",
        "description": "Automatically summarize email threads and extract key action items and decisions",
        "category": "Productivity",
        "tags": ["email", "summarization", "nlp", "productivity"],
        "endpoint_url": "https://seed-agents.brikk.ai/email-summarizer",
        "version": "1.0.0",
        "pricing_model": "free",
        "is_verified": True,
        "is_featured": True
    },
    {
        "agent_id": "code-reviewer",
        "name": "Code Reviewer",
        "description": "Automated code review with best practices, security checks, and improvement suggestions",
        "category": "Development Tools",
        "tags": ["code-review", "security", "best-practices", "development"],
        "endpoint_url": "https://seed-agents.brikk.ai/code-reviewer",
        "version": "1.0.0",
        "pricing_model": "free",
        "is_verified": True,
        "is_featured": True
    }
]

def deploy_seed_agents():
    """Deploy seed agents to the marketplace"""
    
    print("🚀 Deploying Seed Agents to Marketplace\n")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        deployed_count = 0
        
        for agent_config in SEED_AGENTS:
            agent_id = agent_config["agent_id"]
            print(f"\n📦 Processing: {agent_config['name']} ({agent_id})")
            
            # Check if agent already exists
            existing_agent = Agent.query.filter_by(agent_id=agent_id).first()
            
            if existing_agent:
                print(f"   ✓ Agent already exists (ID: {existing_agent.id})")
                agent = existing_agent
            else:
                # Create new agent
                agent = Agent(
                    agent_id=agent_id,
                    name=agent_config["name"],
                    description=agent_config["description"],
                    endpoint_url=agent_config["endpoint_url"],
                    version=agent_config["version"],
                    is_active=True,
                    owner_id=1  # System owner
                )
                db.session.add(agent)
                db.session.flush()
                print(f"   ✓ Agent created (ID: {agent.id})")
            
            # Check if marketplace listing exists
            existing_listing = MarketplaceListing.query.filter_by(agent_id=agent.id).first()
            
            if existing_listing:
                print(f"   ✓ Marketplace listing already exists")
                # Update listing
                existing_listing.category = agent_config["category"]
                existing_listing.tags = agent_config["tags"]
                existing_listing.pricing_model = agent_config["pricing_model"]
                existing_listing.is_verified = agent_config["is_verified"]
                existing_listing.is_featured = agent_config["is_featured"]
                print(f"   ✓ Marketplace listing updated")
            else:
                # Create marketplace listing
                listing = MarketplaceListing(
                    agent_id=agent.id,
                    category=agent_config["category"],
                    tags=agent_config["tags"],
                    pricing_model=agent_config["pricing_model"],
                    is_verified=agent_config["is_verified"],
                    is_featured=agent_config["is_featured"],
                    total_installs=0,
                    average_rating=5.0
                )
                db.session.add(listing)
                print(f"   ✓ Marketplace listing created")
            
            deployed_count += 1
        
        # Commit all changes
        db.session.commit()
        
        print("\n" + "=" * 60)
        print(f"\n✅ Successfully deployed {deployed_count} seed agents!")
        print("\n📊 Marketplace Status:")
        print(f"   Total Agents: {Agent.query.count()}")
        print(f"   Marketplace Listings: {MarketplaceListing.query.count()}")
        print(f"   Featured Agents: {MarketplaceListing.query.filter_by(is_featured=True).count()}")
        print(f"   Verified Agents: {MarketplaceListing.query.filter_by(is_verified=True).count()}")
        
        print("\n🔗 Test Marketplace Endpoints:")
        print("   GET /api/v1/marketplace/agents")
        print("   GET /api/v1/marketplace/categories")
        print("   GET /api/v1/marketplace/trending")
        print("   GET /api/v1/marketplace/featured")
        print("\n")

if __name__ == "__main__":
    try:
        deploy_seed_agents()
    except Exception as e:
        print(f"\n❌ Error deploying seed agents: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

