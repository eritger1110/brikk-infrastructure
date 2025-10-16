# -*- coding: utf-8 -*-
"""
Unit tests for Risk Middleware (Phase 7 PR-3).
"""
import pytest
from src.services.risk_middleware import RiskMiddleware


def test_risk_middleware_initialization():
    """Test RiskMiddleware initialization."""
    middleware = RiskMiddleware()
    
    assert middleware.LOW_RISK_THRESHOLD == 70
    assert middleware.HIGH_RISK_THRESHOLD == 40
    assert middleware.RISK_MULTIPLIERS['low'] == 1.2
    assert middleware.RISK_MULTIPLIERS['med'] == 1.0
    assert middleware.RISK_MULTIPLIERS['high'] == 0.5


def test_classify_risk_low():
    """Test risk classification for low risk."""
    middleware = RiskMiddleware()
    
    assert middleware._classify_risk(100) == 'low'
    assert middleware._classify_risk(85) == 'low'
    assert middleware._classify_risk(70) == 'low'


def test_classify_risk_medium():
    """Test risk classification for medium risk."""
    middleware = RiskMiddleware()
    
    assert middleware._classify_risk(69) == 'med'
    assert middleware._classify_risk(55) == 'med'
    assert middleware._classify_risk(40) == 'med'


def test_classify_risk_high():
    """Test risk classification for high risk."""
    middleware = RiskMiddleware()
    
    assert middleware._classify_risk(39) == 'high'
    assert middleware._classify_risk(20) == 'high'
    assert middleware._classify_risk(0) == 'high'


def test_bucket_score():
    """Test risk score bucketing for privacy."""
    middleware = RiskMiddleware()
    
    assert middleware._bucket_score(0) == '0-20'
    assert middleware._bucket_score(15) == '0-20'
    assert middleware._bucket_score(25) == '20-40'
    assert middleware._bucket_score(45) == '40-60'
    assert middleware._bucket_score(65) == '60-80'
    assert middleware._bucket_score(85) == '80-100'
    assert middleware._bucket_score(100) == '100-120'


def test_get_adaptive_limit_multiplier_low():
    """Test adaptive limit multiplier for low risk."""
    middleware = RiskMiddleware()
    
    multiplier = middleware.get_adaptive_limit_multiplier('low')
    assert multiplier == 1.2


def test_get_adaptive_limit_multiplier_medium():
    """Test adaptive limit multiplier for medium risk."""
    middleware = RiskMiddleware()
    
    multiplier = middleware.get_adaptive_limit_multiplier('med')
    assert multiplier == 1.0


def test_get_adaptive_limit_multiplier_high():
    """Test adaptive limit multiplier for high risk."""
    middleware = RiskMiddleware()
    
    multiplier = middleware.get_adaptive_limit_multiplier('high')
    assert multiplier == 0.5


def test_compute_risk_events_score_no_events():
    """Test risk events score with no events."""
    # This would require a mock DB, but we can test the logic
    # In a real implementation, we'd use fixtures
    pass


def test_compute_auth_score_no_failures():
    """Test auth score with no failures."""
    # This would require a mock DB
    pass


def test_risk_thresholds():
    """Test that risk thresholds are properly ordered."""
    middleware = RiskMiddleware()
    
    # LOW_RISK_THRESHOLD should be higher than HIGH_RISK_THRESHOLD
    assert middleware.LOW_RISK_THRESHOLD > middleware.HIGH_RISK_THRESHOLD
    
    # Thresholds should be in valid range
    assert 0 <= middleware.HIGH_RISK_THRESHOLD <= 100
    assert 0 <= middleware.LOW_RISK_THRESHOLD <= 100


def test_risk_multipliers_valid():
    """Test that risk multipliers are valid."""
    middleware = RiskMiddleware()
    
    # All multipliers should be positive
    for level, multiplier in middleware.RISK_MULTIPLIERS.items():
        assert multiplier > 0
        assert multiplier <= 2.0  # Reasonable upper bound
    
    # High risk should have lowest multiplier
    assert middleware.RISK_MULTIPLIERS['high'] < middleware.RISK_MULTIPLIERS['med']
    assert middleware.RISK_MULTIPLIERS['high'] < middleware.RISK_MULTIPLIERS['low']
    
    # Low risk should have highest multiplier
    assert middleware.RISK_MULTIPLIERS['low'] > middleware.RISK_MULTIPLIERS['med']
    assert middleware.RISK_MULTIPLIERS['low'] > middleware.RISK_MULTIPLIERS['high']

