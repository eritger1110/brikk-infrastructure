"""
Phase 7 Integration Tests
Tests all Phase 7 endpoints end-to-end
"""
import pytest
import json
from datetime import datetime, timedelta
from flask import Flask

from src.factory import create_app
from src.database import db
from src.models.agent import Agent
from src.models.marketplace import MarketplaceListing, MarketplaceCategory, MarketplaceTag
from src.models.analytics import AgentUsageEvent
from src.models.reviews import AgentReview


@pytest.fixture
def app():
    """Create test app"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def test_agent(app):
    """Create a test agent"""
    with app.app_context():
        agent = Agent(
            id='test-agent-123',
            name='Test Agent',
            description='A test agent',
            owner_id='test-user',
            endpoint_url='https://example.com/agent',
            status='active'
        )
        db.session.add(agent)
        db.session.commit()
        return agent.id


@pytest.fixture
def test_category(app):
    """Create a test category"""
    with app.app_context():
        category = MarketplaceCategory(
            id='test-category',
            name='Test Category',
            description='A test category',
            slug='test-category'
        )
        db.session.add(category)
        db.session.commit()
        return category.id


# =============================================================================
# MARKETPLACE TESTS
# =============================================================================

class TestMarketplace:
    """Test marketplace endpoints"""
    
    def test_list_agents_feature_disabled(self, client):
        """Test listing agents when feature is disabled"""
        response = client.get('/api/v1/marketplace/agents')
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['error'] == 'marketplace_disabled'
        assert 'enabled' in data
        assert data['enabled'] == False
    
    def test_get_categories(self, client, test_category):
        """Test getting categories"""
        response = client.get('/api/v1/marketplace/categories')
        # Should work even if marketplace is disabled (read-only)
        assert response.status_code in [200, 503]
    
    def test_get_tags(self, client):
        """Test getting tags"""
        response = client.get('/api/v1/marketplace/tags')
        assert response.status_code in [200, 503]


# =============================================================================
# ANALYTICS TESTS
# =============================================================================

class TestAnalytics:
    """Test analytics endpoints"""
    
    def test_track_event_feature_disabled(self, client):
        """Test tracking event when feature is disabled"""
        response = client.post('/api/v1/analytics/events', json={
            'agent_id': 'test-agent',
            'event_type': 'invocation',
            'duration_ms': 100,
            'success': True
        })
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data['error'] == 'analytics_disabled'
    
    def test_get_metrics_missing_agent(self, client):
        """Test getting metrics for non-existent agent"""
        response = client.get('/api/v1/analytics/agents/nonexistent/metrics')
        # Should return 503 (feature disabled) or 404 (not found)
        assert response.status_code in [404, 503]
    
    def test_get_trending(self, client):
        """Test getting trending agents"""
        response = client.get('/api/v1/analytics/trending')
        assert response.status_code in [200, 503]


# =============================================================================
# DISCOVERY TESTS
# =============================================================================

class TestDiscovery:
    """Test discovery endpoints"""
    
    def test_search_agents(self, client):
        """Test searching agents"""
        response = client.get('/api/v1/agent-discovery/search?q=test')
        # Should return results or feature disabled
        assert response.status_code in [200, 503]
    
    def test_search_missing_query(self, client):
        """Test search without query parameter"""
        response = client.get('/api/v1/agent-discovery/search')
        # Should return 400 (validation error) or 503 (feature disabled)
        assert response.status_code in [400, 503]
    
    def test_get_recommendations(self, client):
        """Test getting recommendations"""
        response = client.get(
            '/api/v1/agent-discovery/recommendations',
            headers={'X-User-ID': 'test-user'}
        )
        assert response.status_code in [200, 503]
    
    def test_get_similar_agents(self, client, test_agent):
        """Test getting similar agents"""
        response = client.get(f'/api/v1/agent-discovery/similar/{test_agent}')
        assert response.status_code in [200, 404, 503]


# =============================================================================
# REVIEWS TESTS
# =============================================================================

class TestReviews:
    """Test reviews endpoints"""
    
    def test_get_reviews(self, client, test_agent):
        """Test getting reviews for an agent"""
        response = client.get(f'/api/v1/reviews/agents/{test_agent}')
        # Should return reviews or feature disabled
        assert response.status_code in [200, 503]
    
    def test_submit_review_no_auth(self, client, test_agent):
        """Test submitting review without authentication"""
        response = client.post(f'/api/v1/reviews/agents/{test_agent}', json={
            'rating': 5,
            'title': 'Great agent!',
            'comment': 'Works perfectly'
        })
        # Should require auth or feature disabled
        assert response.status_code in [401, 503]
    
    def test_submit_review_invalid_rating(self, client, test_agent):
        """Test submitting review with invalid rating"""
        response = client.post(
            f'/api/v1/reviews/agents/{test_agent}',
            json={
                'rating': 6,  # Invalid: should be 1-5
                'title': 'Test',
                'comment': 'Test'
            },
            headers={'X-User-ID': 'test-user'}
        )
        # Should return validation error or feature disabled
        assert response.status_code in [400, 503]
    
    def test_get_rating_summary(self, client, test_agent):
        """Test getting rating summary"""
        response = client.get(f'/api/v1/reviews/agents/{test_agent}/summary')
        assert response.status_code in [200, 404, 503]


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Test Phase 7 error handling"""
    
    def test_feature_disabled_response_format(self, client):
        """Test that feature disabled responses have consistent format"""
        response = client.get('/api/v1/marketplace/agents')
        assert response.status_code == 503
        data = json.loads(response.data)
        
        # Check required fields
        assert 'error' in data
        assert 'message' in data
        assert 'feature' in data
        assert 'enabled' in data
        
        # Check values
        assert data['enabled'] == False
        assert 'marketplace' in data['error'].lower()
    
    def test_validation_error_format(self, client):
        """Test validation error response format"""
        response = client.post('/api/v1/analytics/events', json={
            # Missing required fields
            'event_type': 'invocation'
        })
        
        if response.status_code == 400:
            data = json.loads(response.data)
            assert 'error' in data
            assert 'message' in data
    
    def test_auth_required_format(self, client, test_agent):
        """Test auth required response format"""
        response = client.post(f'/api/v1/reviews/agents/{test_agent}', json={
            'rating': 5,
            'title': 'Test',
            'comment': 'Test'
        })
        
        if response.status_code == 401:
            data = json.loads(response.data)
            assert 'error' in data
            assert data['error'] == 'auth_required'
            assert 'message' in data


# =============================================================================
# FEATURE FLAG TESTS
# =============================================================================

class TestFeatureFlags:
    """Test feature flag integration"""
    
    def test_marketplace_flag(self, client):
        """Test marketplace feature flag"""
        response = client.get('/api/v1/marketplace/agents')
        data = json.loads(response.data)
        
        # Should indicate marketplace is disabled
        if response.status_code == 503:
            assert 'marketplace' in data.get('error', '').lower()
    
    def test_analytics_flag(self, client):
        """Test analytics feature flag"""
        response = client.post('/api/v1/analytics/events', json={
            'agent_id': 'test',
            'event_type': 'invocation',
            'success': True
        })
        data = json.loads(response.data)
        
        # Should indicate analytics is disabled
        if response.status_code == 503:
            assert 'analytics' in data.get('error', '').lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

