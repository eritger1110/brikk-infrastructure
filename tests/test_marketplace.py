"""
Tests for marketplace functionality
"""
import pytest
import uuid
from datetime import datetime, timezone, timedelta

from src.models.marketplace import (
    MarketplaceListing,
    AgentCategory,
    AgentTag,
    AgentInstallation
)
from src.models.agent import Agent
from src.infra.db import db


@pytest.fixture
def sample_agent(app):
    """Create a sample agent for testing"""
    with app.app_context():
        agent = Agent(
            id=str(uuid.uuid4()),
            name='Test Agent',
            version='1.0.0',
            status='active'
        )
        db.session.add(agent)
        db.session.commit()
        yield agent
        db.session.delete(agent)
        db.session.commit()


@pytest.fixture
def sample_listing(app, sample_agent):
    """Create a sample marketplace listing"""
    with app.app_context():
        listing = MarketplaceListing(
            agent_id=sample_agent.id,
            publisher_id='test-user-123',
            status='published',
            visibility='public',
            category='productivity',
            tags=['automation', 'productivity'],
            short_description='A test agent',
            long_description='This is a test agent for unit testing',
            pricing_model='free'
        )
        db.session.add(listing)
        db.session.commit()
        yield listing
        db.session.delete(listing)
        db.session.commit()


class TestMarketplaceListing:
    """Test MarketplaceListing model"""
    
    def test_create_listing(self, app, sample_agent):
        """Test creating a marketplace listing"""
        with app.app_context():
            listing = MarketplaceListing(
                agent_id=sample_agent.id,
                publisher_id='user-123',
                status='draft',
                short_description='Test listing'
            )
            db.session.add(listing)
            db.session.commit()
            
            assert listing.id is not None
            assert listing.agent_id == sample_agent.id
            assert listing.status == 'draft'
            assert listing.install_count == 0
            assert listing.view_count == 0
            
            db.session.delete(listing)
            db.session.commit()
    
    def test_increment_views(self, app, sample_listing):
        """Test incrementing view count"""
        with app.app_context():
            initial_views = sample_listing.view_count
            sample_listing.increment_views()
            
            assert sample_listing.view_count == initial_views + 1
    
    def test_increment_installs(self, app, sample_listing):
        """Test incrementing install count"""
        with app.app_context():
            initial_installs = sample_listing.install_count
            sample_listing.increment_installs()
            
            assert sample_listing.install_count == initial_installs + 1
    
    def test_publish_listing(self, app, sample_agent):
        """Test publishing a listing"""
        with app.app_context():
            listing = MarketplaceListing(
                agent_id=sample_agent.id,
                publisher_id='user-123',
                status='draft'
            )
            db.session.add(listing)
            db.session.commit()
            
            assert listing.status == 'draft'
            assert listing.published_at is None
            
            listing.publish()
            
            assert listing.status == 'published'
            assert listing.published_at is not None
            
            db.session.delete(listing)
            db.session.commit()
    
    def test_archive_listing(self, app, sample_listing):
        """Test archiving a listing"""
        with app.app_context():
            sample_listing.archive()
            assert sample_listing.status == 'archived'
    
    def test_to_dict(self, app, sample_listing):
        """Test converting listing to dictionary"""
        with app.app_context():
            listing_dict = sample_listing.to_dict()
            
            assert listing_dict['id'] == sample_listing.id
            assert listing_dict['agent_id'] == sample_listing.agent_id
            assert listing_dict['status'] == 'published'
            assert listing_dict['tags'] == ['automation', 'productivity']
            assert listing_dict['pricing_model'] == 'free'


class TestAgentCategory:
    """Test AgentCategory model"""
    
    def test_create_category(self, app):
        """Test creating a category"""
        with app.app_context():
            category = AgentCategory(
                name='Test Category',
                slug='test-category',
                description='A test category',
                display_order=1
            )
            db.session.add(category)
            db.session.commit()
            
            assert category.id is not None
            assert category.name == 'Test Category'
            assert category.slug == 'test-category'
            
            db.session.delete(category)
            db.session.commit()
    
    def test_category_hierarchy(self, app):
        """Test category parent-child relationship"""
        with app.app_context():
            parent = AgentCategory(
                name='Parent Category',
                slug='parent-category'
            )
            db.session.add(parent)
            db.session.commit()
            
            child = AgentCategory(
                name='Child Category',
                slug='child-category',
                parent_id=parent.id
            )
            db.session.add(child)
            db.session.commit()
            
            assert child.parent_id == parent.id
            assert child.parent == parent
            assert child in parent.children
            
            db.session.delete(child)
            db.session.delete(parent)
            db.session.commit()


class TestAgentTag:
    """Test AgentTag model"""
    
    def test_create_tag(self, app):
        """Test creating a tag"""
        with app.app_context():
            tag = AgentTag(
                name='Test Tag',
                slug='test-tag'
            )
            db.session.add(tag)
            db.session.commit()
            
            assert tag.id is not None
            assert tag.name == 'Test Tag'
            assert tag.usage_count == 0
            
            db.session.delete(tag)
            db.session.commit()
    
    def test_increment_usage(self, app):
        """Test incrementing tag usage count"""
        with app.app_context():
            tag = AgentTag(
                name='Popular Tag',
                slug='popular-tag'
            )
            db.session.add(tag)
            db.session.commit()
            
            initial_count = tag.usage_count
            tag.increment_usage()
            
            assert tag.usage_count == initial_count + 1
            
            db.session.delete(tag)
            db.session.commit()


class TestAgentInstallation:
    """Test AgentInstallation model"""
    
    def test_create_installation(self, app, sample_agent):
        """Test creating an installation record"""
        with app.app_context():
            installation = AgentInstallation(
                agent_id=sample_agent.id,
                user_id='user-123',
                installed_version='1.0.0'
            )
            db.session.add(installation)
            db.session.commit()
            
            assert installation.id is not None
            assert installation.agent_id == sample_agent.id
            assert installation.user_id == 'user-123'
            assert installation.uninstalled_at is None
            
            db.session.delete(installation)
            db.session.commit()
    
    def test_uninstall(self, app, sample_agent):
        """Test uninstalling an agent"""
        with app.app_context():
            installation = AgentInstallation(
                agent_id=sample_agent.id,
                user_id='user-123'
            )
            db.session.add(installation)
            db.session.commit()
            
            assert installation.uninstalled_at is None
            
            installation.uninstall()
            
            assert installation.uninstalled_at is not None
            
            db.session.delete(installation)
            db.session.commit()
    
    def test_update_last_used(self, app, sample_agent):
        """Test updating last used timestamp"""
        with app.app_context():
            installation = AgentInstallation(
                agent_id=sample_agent.id,
                user_id='user-123'
            )
            db.session.add(installation)
            db.session.commit()
            
            assert installation.last_used_at is None
            
            installation.update_last_used()
            
            assert installation.last_used_at is not None
            
            db.session.delete(installation)
            db.session.commit()
    
    def test_to_dict(self, app, sample_agent):
        """Test converting installation to dictionary"""
        with app.app_context():
            installation = AgentInstallation(
                agent_id=sample_agent.id,
                user_id='user-123',
                installed_version='1.0.0'
            )
            db.session.add(installation)
            db.session.commit()
            
            install_dict = installation.to_dict()
            
            assert install_dict['agent_id'] == sample_agent.id
            assert install_dict['user_id'] == 'user-123'
            assert install_dict['is_active'] is True
            
            installation.uninstall()
            install_dict = installation.to_dict()
            assert install_dict['is_active'] is False
            
            db.session.delete(installation)
            db.session.commit()


class TestMarketplaceQueries:
    """Test marketplace query scenarios"""
    
    def test_filter_by_category(self, app, sample_agent):
        """Test filtering listings by category"""
        with app.app_context():
            listing1 = MarketplaceListing(
                agent_id=sample_agent.id,
                publisher_id='user-123',
                status='published',
                category='productivity'
            )
            db.session.add(listing1)
            db.session.commit()
            
            results = MarketplaceListing.query.filter_by(
                status='published',
                category='productivity'
            ).all()
            
            assert len(results) >= 1
            assert any(l.id == listing1.id for l in results)
            
            db.session.delete(listing1)
            db.session.commit()
    
    def test_filter_by_featured(self, app, sample_agent):
        """Test filtering featured listings"""
        with app.app_context():
            listing = MarketplaceListing(
                agent_id=sample_agent.id,
                publisher_id='user-123',
                status='published',
                featured=True,
                featured_until=datetime.now(timezone.utc) + timedelta(days=7)
            )
            db.session.add(listing)
            db.session.commit()
            
            results = MarketplaceListing.query.filter_by(
                status='published',
                featured=True
            ).filter(
                (MarketplaceListing.featured_until == None) |
                (MarketplaceListing.featured_until > datetime.now(timezone.utc))
            ).all()
            
            assert len(results) >= 1
            assert any(l.id == listing.id for l in results)
            
            db.session.delete(listing)
            db.session.commit()
    
    def test_sort_by_popularity(self, app, sample_agent):
        """Test sorting by install count"""
        with app.app_context():
            listing = MarketplaceListing(
                agent_id=sample_agent.id,
                publisher_id='user-123',
                status='published',
                install_count=100
            )
            db.session.add(listing)
            db.session.commit()
            
            results = MarketplaceListing.query.filter_by(
                status='published'
            ).order_by(MarketplaceListing.install_count.desc()).all()
            
            assert len(results) >= 1
            # Most popular should be first
            if len(results) > 1:
                assert results[0].install_count >= results[1].install_count
            
            db.session.delete(listing)
            db.session.commit()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

