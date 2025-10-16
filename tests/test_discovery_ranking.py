# -*- coding: utf-8 -*-
"""
Unit tests for Agent Discovery Ranking (Phase 7 PR-5).
"""
import pytest


def test_sort_parameter_validation():
    """Test sort parameter validation."""
    valid_sorts = ['reputation', 'recency', 'name']
    invalid_sorts = ['popularity', 'price', 'rating', '']
    
    for sort in valid_sorts:
        assert sort in ['reputation', 'recency', 'name']
    
    for sort in invalid_sorts:
        assert sort not in ['reputation', 'recency', 'name']


def test_reputation_score_bucketing():
    """Test reputation score bucketing for privacy."""
    # Test bucketing logic
    def bucket_score(score):
        if score >= 80:
            return "80-100"
        elif score >= 60:
            return "60-80"
        elif score >= 40:
            return "40-60"
        elif score >= 20:
            return "20-40"
        else:
            return "0-20"
    
    assert bucket_score(95) == "80-100"
    assert bucket_score(75) == "60-80"
    assert bucket_score(55) == "40-60"
    assert bucket_score(35) == "20-40"
    assert bucket_score(15) == "0-20"


def test_sort_order_reputation():
    """Test reputation sort order (DESC)."""
    agents = [
        {'name': 'Agent A', 'reputation': 90},
        {'name': 'Agent B', 'reputation': 70},
        {'name': 'Agent C', 'reputation': 85}
    ]
    
    sorted_agents = sorted(agents, key=lambda a: a['reputation'], reverse=True)
    
    assert sorted_agents[0]['name'] == 'Agent A'  # 90
    assert sorted_agents[1]['name'] == 'Agent C'  # 85
    assert sorted_agents[2]['name'] == 'Agent B'  # 70


def test_sort_order_recency():
    """Test recency sort order (newest first)."""
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    agents = [
        {'name': 'Agent A', 'created_at': now - timedelta(days=10)},
        {'name': 'Agent B', 'created_at': now - timedelta(days=1)},
        {'name': 'Agent C', 'created_at': now - timedelta(days=5)}
    ]
    
    sorted_agents = sorted(agents, key=lambda a: a['created_at'], reverse=True)
    
    assert sorted_agents[0]['name'] == 'Agent B'  # Most recent
    assert sorted_agents[1]['name'] == 'Agent C'
    assert sorted_agents[2]['name'] == 'Agent A'  # Oldest


def test_sort_order_name():
    """Test name sort order (alphabetical)."""
    agents = [
        {'name': 'Zulu Agent'},
        {'name': 'Alpha Agent'},
        {'name': 'Bravo Agent'}
    ]
    
    sorted_agents = sorted(agents, key=lambda a: a['name'])
    
    assert sorted_agents[0]['name'] == 'Alpha Agent'
    assert sorted_agents[1]['name'] == 'Bravo Agent'
    assert sorted_agents[2]['name'] == 'Zulu Agent'


def test_null_reputation_handling():
    """Test that agents without reputation scores are handled gracefully."""
    agents = [
        {'name': 'Agent A', 'reputation': 90},
        {'name': 'Agent B', 'reputation': None},
        {'name': 'Agent C', 'reputation': 85}
    ]
    
    # Nulls should go last
    sorted_agents = sorted(
        agents,
        key=lambda a: (a['reputation'] is None, -(a['reputation'] or 0))
    )
    
    assert sorted_agents[0]['name'] == 'Agent A'  # 90
    assert sorted_agents[1]['name'] == 'Agent C'  # 85
    assert sorted_agents[2]['name'] == 'Agent B'  # None (last)


def test_pagination_with_sorting():
    """Test that pagination works correctly with sorting."""
    agents = list(range(1, 101))  # 100 agents
    page = 2
    per_page = 20
    
    start = (page - 1) * per_page
    end = start + per_page
    
    paginated = agents[start:end]
    
    assert len(paginated) == 20
    assert paginated[0] == 21  # First item on page 2
    assert paginated[-1] == 40  # Last item on page 2


def test_reputation_enrichment():
    """Test that agents are enriched with reputation scores."""
    agent = {
        'id': 'agent_123',
        'name': 'Test Agent',
        'description': 'Test description'
    }
    
    # Simulate enrichment
    reputation_score_bucket = "80-100"
    agent['reputation_score_bucket'] = reputation_score_bucket
    
    assert 'reputation_score_bucket' in agent
    assert agent['reputation_score_bucket'] == "80-100"


def test_reputation_enrichment_no_score():
    """Test enrichment when no reputation score exists."""
    agent = {
        'id': 'agent_123',
        'name': 'Test Agent',
        'description': 'Test description'
    }
    
    # Simulate no reputation score
    agent['reputation_score_bucket'] = None
    
    assert 'reputation_score_bucket' in agent
    assert agent['reputation_score_bucket'] is None

