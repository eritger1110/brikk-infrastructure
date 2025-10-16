# -*- coding: utf-8 -*-
"""
Unit tests for Reputation Engine (Phase 7 PR-2).
"""
import pytest
from datetime import datetime, timedelta
from src.services.reputation_engine import ReputationEngine


class MockDB:
    """Mock database for testing."""
    def query(self, *args, **kwargs):
        return MockQuery()


class MockQuery:
    """Mock query for testing."""
    def filter(self, *args, **kwargs):
        return self
    
    def all(self):
        return []
    
    def count(self):
        return 0
    
    def scalar(self):
        return 0
    
    def first(self):
        return None


def test_reputation_engine_initialization():
    """Test ReputationEngine initialization."""
    db = MockDB()
    engine = ReputationEngine(db)
    
    assert engine.db == db
    assert engine.WEIGHTS['reliability'] == 0.30
    assert engine.WEIGHTS['commerce'] == 0.20
    assert engine.WEIGHTS['hygiene'] == 0.15
    assert engine.WEIGHTS['attestations'] == 0.20
    assert engine.WEIGHTS['usage'] == 0.15
    
    # Weights should sum to 1.0
    total_weight = sum(engine.WEIGHTS.values())
    assert abs(total_weight - 1.0) < 0.001


def test_parse_window():
    """Test window parsing."""
    db = MockDB()
    engine = ReputationEngine(db)
    
    assert engine._parse_window('7d') == 7
    assert engine._parse_window('30d') == 30
    assert engine._parse_window('90d') == 90
    assert engine._parse_window('invalid') == 30  # Default


def test_bucket_score():
    """Test score bucketing for privacy."""
    db = MockDB()
    engine = ReputationEngine(db)
    
    assert engine.bucket_score(0) == '0-10'
    assert engine.bucket_score(5) == '0-10'
    assert engine.bucket_score(15) == '10-20'
    assert engine.bucket_score(45) == '40-50'
    assert engine.bucket_score(85) == '80-90'
    assert engine.bucket_score(95) == '90-100'
    assert engine.bucket_score(100) == '100-110'  # Edge case


def test_compute_score_no_data():
    """Test score computation with no data (neutral scores)."""
    db = MockDB()
    engine = ReputationEngine(db)
    
    score, reason = engine.compute_score('org', 'org_123', '30d')
    
    # With no data, should get neutral scores
    assert 0 <= score <= 100
    assert 'factors' in reason
    assert 'reliability' in reason['factors']
    assert 'commerce' in reason['factors']
    assert 'hygiene' in reason['factors']
    assert 'attestations' in reason['factors']
    assert 'usage' in reason['factors']
    
    # Check that each factor has required fields
    for factor_name, factor_data in reason['factors'].items():
        assert 'score' in factor_data
        assert 'weight' in factor_data
        assert 'contribution' in factor_data


def test_get_top_factors():
    """Test extraction of top contributing factors."""
    db = MockDB()
    engine = ReputationEngine(db)
    
    reason = {
        'factors': {
            'reliability': {'score': 90, 'weight': 0.3, 'contribution': 27},
            'commerce': {'score': 80, 'weight': 0.2, 'contribution': 16},
            'hygiene': {'score': 95, 'weight': 0.15, 'contribution': 14.25},
            'attestations': {'score': 70, 'weight': 0.2, 'contribution': 14},
            'usage': {'score': 85, 'weight': 0.15, 'contribution': 12.75}
        }
    }
    
    top_factors = engine.get_top_factors(reason, limit=3)
    
    assert len(top_factors) == 3
    assert top_factors[0]['factor'] == 'reliability'
    assert top_factors[1]['factor'] == 'commerce'
    assert top_factors[2]['factor'] == 'hygiene'


def test_compute_reliability_no_logs():
    """Test reliability computation with no logs."""
    db = MockDB()
    engine = ReputationEngine(db)
    
    cutoff = datetime.utcnow() - timedelta(days=30)
    score = engine._compute_reliability('org', 'org_123', cutoff)
    
    # Should return neutral score
    assert score == 75.0


def test_compute_commerce_no_usage():
    """Test commerce computation with no usage."""
    db = MockDB()
    engine = ReputationEngine(db)
    
    cutoff = datetime.utcnow() - timedelta(days=30)
    score = engine._compute_commerce('org', 'org_123', cutoff)
    
    # Should return baseline score
    assert 0 <= score <= 100


def test_compute_hygiene_no_events():
    """Test hygiene computation with no risk events."""
    db = MockDB()
    engine = ReputationEngine(db)
    
    cutoff = datetime.utcnow() - timedelta(days=30)
    score = engine._compute_hygiene('org', 'org_123', cutoff)
    
    # Should return perfect score (no issues)
    assert score == 100.0


def test_compute_attestations_no_attestations():
    """Test attestations computation with no attestations."""
    db = MockDB()
    engine = ReputationEngine(db)
    
    cutoff = datetime.utcnow() - timedelta(days=30)
    score = engine._compute_attestations('org', 'org_123', cutoff)
    
    # Should return neutral score
    assert score == 50.0


def test_compute_usage_no_usage():
    """Test usage computation with no usage."""
    db = MockDB()
    engine = ReputationEngine(db)
    
    cutoff = datetime.utcnow() - timedelta(days=30)
    score = engine._compute_usage('org', 'org_123', cutoff)
    
    # Should return neutral score
    assert score == 50.0


def test_score_clamping():
    """Test that scores are clamped to 0-100 range."""
    db = MockDB()
    engine = ReputationEngine(db)
    
    # Test with various inputs to ensure clamping works
    score1, _ = engine.compute_score('org', 'org_123', '7d')
    assert 0 <= score1 <= 100
    
    score2, _ = engine.compute_score('agent', 'agent_456', '30d')
    assert 0 <= score2 <= 100
    
    score3, _ = engine.compute_score('org', 'org_789', '90d')
    assert 0 <= score3 <= 100

