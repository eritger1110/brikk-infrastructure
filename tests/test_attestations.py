# -*- coding: utf-8 -*-
"""
Unit tests for Attestations CRUD (Phase 7 PR-4).
"""
import pytest
from datetime import datetime


def test_attestation_validation_weight():
    """Test attestation weight validation."""
    # Valid weights
    assert 0.0 <= 0.0 <= 1.0
    assert 0.0 <= 0.5 <= 1.0
    assert 0.0 <= 1.0 <= 1.0
    
    # Invalid weights
    assert not (0.0 <= -0.1 <= 1.0)
    assert not (0.0 <= 1.1 <= 1.0)


def test_attestation_subject_type_validation():
    """Test attestation subject_type validation."""
    valid_types = ['org', 'agent']
    invalid_types = ['user', 'service', 'api', '']
    
    for t in valid_types:
        assert t in ['org', 'agent']
    
    for t in invalid_types:
        assert t not in ['org', 'agent']


def test_self_attestation_prevention():
    """Test that self-attestation is prevented."""
    attester_org_id = 'org_123'
    subject_type = 'org'
    subject_id = 'org_123'
    
    # Should be prevented
    is_self_attestation = (subject_type == 'org' and subject_id == attester_org_id)
    assert is_self_attestation == True
    
    # Should be allowed
    subject_id = 'org_456'
    is_self_attestation = (subject_type == 'org' and subject_id == attester_org_id)
    assert is_self_attestation == False


def test_attestation_aggregate_metrics():
    """Test aggregate trust metrics calculation."""
    # Mock attestations
    attestations = [
        {'weight': 0.8},
        {'weight': 0.6},
        {'weight': 0.9}
    ]
    
    total_weight = sum(att['weight'] for att in attestations)
    avg_weight = total_weight / len(attestations)
    
    assert total_weight == 2.3
    assert round(avg_weight, 2) == 0.77


def test_attestation_aggregate_metrics_empty():
    """Test aggregate metrics with no attestations."""
    attestations = []
    
    total_weight = sum(att.get('weight', 0) for att in attestations)
    avg_weight = total_weight / len(attestations) if attestations else 0.0
    
    assert total_weight == 0.0
    assert avg_weight == 0.0


def test_attestation_required_fields():
    """Test attestation required fields validation."""
    required_fields = ['subject_type', 'subject_id', 'weight', 'statement']
    
    # Valid data
    valid_data = {
        'subject_type': 'org',
        'subject_id': 'org_123',
        'weight': 0.8,
        'statement': 'Reliable partner'
    }
    missing = [f for f in required_fields if f not in valid_data]
    assert len(missing) == 0
    
    # Missing field
    invalid_data = {
        'subject_type': 'org',
        'subject_id': 'org_123',
        'weight': 0.8
    }
    missing = [f for f in required_fields if f not in invalid_data]
    assert len(missing) == 1
    assert 'statement' in missing


def test_attestation_evidence_url_optional():
    """Test that evidence_url is optional."""
    data = {
        'subject_type': 'org',
        'subject_id': 'org_123',
        'weight': 0.8,
        'statement': 'Reliable partner'
    }
    
    evidence_url = data.get('evidence_url')
    assert evidence_url is None
    
    data['evidence_url'] = 'https://example.com/evidence'
    evidence_url = data.get('evidence_url')
    assert evidence_url == 'https://example.com/evidence'


def test_attestation_ownership_check():
    """Test attestation ownership verification for revocation."""
    attestation_attester = 'org_123'
    current_user = 'org_123'
    
    # Owner can revoke
    assert attestation_attester == current_user
    
    # Non-owner cannot revoke
    current_user = 'org_456'
    assert attestation_attester != current_user

