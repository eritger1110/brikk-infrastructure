#!/usr/bin/env python3
"""
Seed Agents Script
Creates three demo agents in the marketplace for the beta program
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import db
from src.models.agent import Agent
from src.models.marketplace import MarketplaceListing
from src.factory import create_app
from datetime import datetime, timezone
import uuid

def seed_agents():
    """Create three seed agents in the marketplace"""
    
    app = create_app()
    
    with app.app_context():
        print("🚀 Seeding demo agents to marketplace...")
        print("")
        
        # Agent 1: CSV Analyzer
        print("📊 Creating CSV Analyzer...")
        agent1_id = str(uuid.uuid4())
        agent1 = Agent(
            id=agent1_id,
            name="CSV Analyzer",
            description="Analyze CSV files and extract insights, trends, and patterns",
            owner_id="system",
            api_key_hash="seed_agent_no_key",  # Placeholder
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        listing1 = MarketplaceListing(
            agent_id=agent1_id,
            publisher_id="system",
            status="published",
            visibility="public",
            category="data-analysis",
            tags=["csv", "data", "analytics", "insights"],
            short_description="Analyze CSV files and extract insights",
            long_description="A powerful agent that analyzes CSV files to extract insights, identify trends, and detect patterns in your data.",
            icon_url="https://api.dicebear.com/7.x/shapes/svg?seed=csv",
            pricing_model="free",
            price_amount=0.0,
            price_currency="USD",
            featured=True,
            verified=True,
            install_count=0,
            view_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.session.add(agent1)
        db.session.add(listing1)
        print("✅ CSV Analyzer created")
        print("")
        
        # Agent 2: Email Summarizer
        print("📧 Creating Email Summarizer...")
        agent2_id = str(uuid.uuid4())
        agent2 = Agent(
            id=agent2_id,
            name="Email Summarizer",
            description="Summarize email threads and extract action items automatically",
            owner_id="system",
            api_key_hash="seed_agent_no_key",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        listing2 = MarketplaceListing(
            agent_id=agent2_id,
            publisher_id="system",
            status="published",
            visibility="public",
            category="productivity",
            tags=["email", "summarization", "productivity", "nlp"],
            short_description="Summarize emails and extract action items",
            long_description="An intelligent agent that automatically summarizes email threads, extracts action items, and provides sentiment analysis.",
            icon_url="https://api.dicebear.com/7.x/shapes/svg?seed=email",
            pricing_model="free",
            price_amount=0.0,
            price_currency="USD",
            featured=True,
            verified=True,
            install_count=0,
            view_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.session.add(agent2)
        db.session.add(listing2)
        print("✅ Email Summarizer created")
        print("")
        
        # Agent 3: Code Reviewer
        print("💻 Creating Code Reviewer...")
        agent3_id = str(uuid.uuid4())
        agent3 = Agent(
            id=agent3_id,
            name="Code Reviewer",
            description="Review code and provide improvement suggestions, bug detection, and best practices",
            owner_id="system",
            api_key_hash="seed_agent_no_key",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        listing3 = MarketplaceListing(
            agent_id=agent3_id,
            publisher_id="system",
            status="published",
            visibility="public",
            category="development",
            tags=["code-review", "static-analysis", "best-practices", "quality"],
            short_description="Review code and suggest improvements",
            long_description="A comprehensive code review agent that analyzes your code, detects bugs, suggests improvements, and enforces best practices.",
            icon_url="https://api.dicebear.com/7.x/shapes/svg?seed=code",
            pricing_model="free",
            price_amount=0.0,
            price_currency="USD",
            featured=True,
            verified=True,
            install_count=0,
            view_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db.session.add(agent3)
        db.session.add(listing3)
        print("✅ Code Reviewer created")
        print("")
        
        # Commit all changes
        db.session.commit()
        
        print("✅ All seed agents created successfully!")
        print("")
        print("Verify with:")
        print("  curl https://brikk-infrastructure.onrender.com/api/v1/marketplace/featured")

if __name__ == "__main__":
    seed_agents()

