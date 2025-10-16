# -*- coding: utf-8 -*-
"""
Unit tests for Trust Layer models (Phase 7 PR-1).
"""
import pytest
from src.models.trust import ReputationSnapshot, Attestation, RiskEvent


def test_reputation_snapshot_creation():
    """Test ReputationSnapshot model instantiation."""
    snapshot = ReputationSnapshot(
        subject_type='org',
        subject_id='org_123',
        score=85,
        window='30d',
        reason={'reliability': 0.4, 'attestations': 0.3, 'usage': 0.3}
    )
    
    assert snapshot.subject_type == 'org'
    assert snapshot.subject_id == 'org_123'
    assert snapshot.score == 85
    assert snapshot.window == '30d'
    assert 'reliability' in snapshot.reason


def test_reputation_snapshot_to_dict():
    """Test ReputationSnapshot to_dict method."""
    snapshot = ReputationSnapshot(
        subject_type='agent',
        subject_id='agent_456',
        score=72,
        window='7d',
        reason={'factor1': 0.5, 'factor2': 0.5}
    )
    
    data = snapshot.to_dict()
    assert data['subject_type'] == 'agent'
    assert data['subject_id'] == 'agent_456'
    assert data['score'] == 72
    assert data['window'] == '7d'


def test_attestation_creation():
    """Test Attestation model instantiation."""
    attestation = Attestation(
        issuer_org='org_123',
        subject_type='agent',
        subject_id='agent_456',
        scopes=['reliability', 'quality'],
        weight=5,
        note='Great service provider'
    )
    
    assert attestation.issuer_org == 'org_123'
    assert attestation.subject_type == 'agent'
    assert attestation.subject_id == 'agent_456'
    assert 'reliability' in attestation.scopes
    assert attestation.weight == 5


def test_attestation_to_dict():
    """Test Attestation to_dict method."""
    attestation = Attestation(
        issuer_org='org_789',
        subject_type='org',
        subject_id='org_101',
        scopes=['support', 'communication'],
        weight=3
    )
    
    data = attestation.to_dict()
    assert data['issuer_org'] == 'org_789'
    assert data['subject_type'] == 'org'
    assert data['scopes'] == ['support', 'communication']
    assert data['weight'] == 3


def test_risk_event_creation():
    """Test RiskEvent model instantiation."""
    event = RiskEvent(
        org_id='org_123',
        actor_id='key_456',
        type='auth_fail',
        severity='med',
        meta={'attempts': 5, 'ip': '192.168.1.1'}
    )
    
    assert event.org_id == 'org_123'
    assert event.actor_id == 'key_456'
    assert event.type == 'auth_fail'
    assert event.severity == 'med'
    assert event.meta['attempts'] == 5


def test_risk_event_to_dict():
    """Test RiskEvent to_dict method."""
    event = RiskEvent(
        org_id='org_789',
        type='rate_limit_spike',
        severity='high',
        meta={'threshold': 1000, 'actual': 2500}
    )
    
    data = event.to_dict()
    assert data['org_id'] == 'org_789'
    assert data['type'] == 'rate_limit_spike'
    assert data['severity'] == 'high'
    assert data['meta']['actual'] == 2500


def test_reputation_score_constraints():
    """Test that reputation scores are constrained to 0-100."""
    # Valid scores
    snapshot1 = ReputationSnapshot(
        subject_type='org',
        subject_id='org_123',
        score=0,
        window='30d',
        reason={}
    )
    assert snapshot1.score == 0
    
    snapshot2 = ReputationSnapshot(
        subject_type='org',
        subject_id='org_123',
        score=100,
        window='30d',
        reason={}
    )
    assert snapshot2.score == 100


def test_attestation_weight_constraints():
    """Test that attestation weights are constrained to 1-10."""
    # Valid weights
    attestation1 = Attestation(
        issuer_org='org_123',
        subject_type='agent',
        subject_id='agent_456',
        scopes=['test'],
        weight=1
    )
    assert attestation1.weight == 1
    
    attestation2 = Attestation(
        issuer_org='org_123',
        subject_type='agent',
        subject_id='agent_456',
        scopes=['test'],
        weight=10
    )
    assert attestation2.weight == 10

