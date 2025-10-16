# -*- coding: utf-8 -*-
"""
Unit tests for Usage Metering (Phase 6 PR-2).

Tests usage ledger recording, cost calculation, and middleware integration.
"""
import pytest
from decimal import Decimal
from datetime import datetime
from src.factory import create_app
from src.database import db
from src.models.usage_ledger import UsageLedger
from src.services.pricing import get_unit_cost, calculate_cost, TIER_PRICING


@pytest.fixture
def app():
    """Create test application."""
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
    """Create test client."""
    return app.test_client()


def test_pricing_config():
    """Test pricing configuration."""
    # Test default tier pricing
    assert get_unit_cost('FREE') == Decimal('0.0000')
    assert get_unit_cost('HACKER') == Decimal('0.0050')
    assert get_unit_cost('STARTER') == Decimal('0.0100')
    assert get_unit_cost('PRO') == Decimal('0.0075')
    assert get_unit_cost('ENT') == Decimal('0.0050')
    assert get_unit_cost('DEFAULT') == Decimal('0.0100')
    
    # Test unknown tier defaults to DEFAULT
    assert get_unit_cost('UNKNOWN') == Decimal('0.0100')
    assert get_unit_cost(None) == Decimal('0.0100')


def test_cost_calculation():
    """Test cost calculation."""
    # Test single unit
    assert calculate_cost('STARTER', 1) == Decimal('0.0100')
    
    # Test multiple units
    assert calculate_cost('STARTER', 100) == Decimal('1.0000')
    
    # Test free tier
    assert calculate_cost('FREE', 1000) == Decimal('0.0000')
    
    # Test PRO tier with volume
    assert calculate_cost('PRO', 1000) == Decimal('7.5000')


def test_usage_ledger_record(app):
    """Test recording usage in ledger."""
    with app.app_context():
        # Record usage
        entry = UsageLedger.record_usage(
            org_id='test-org-123',
            actor_id='api_key:test-key',
            route='/v1/agents',
            unit_cost=Decimal('0.0100'),
            usage_units=1
        )
        
        # Verify entry
        assert entry.id is not None
        assert entry.org_id == 'test-org-123'
        assert entry.actor_id == 'api_key:test-key'
        assert entry.route == '/v1/agents'
        assert entry.usage_units == 1
        assert entry.unit_cost == Decimal('0.0100')
        assert entry.total_cost == Decimal('0.0100')
        assert entry.billed_at is None


def test_usage_ledger_get_unbilled(app):
    """Test getting unbilled entries."""
    with app.app_context():
        # Create test entries
        UsageLedger.record_usage(
            org_id='org-1',
            actor_id='key-1',
            route='/v1/test',
            unit_cost=Decimal('0.01')
        )
        
        UsageLedger.record_usage(
            org_id='org-2',
            actor_id='key-2',
            route='/v1/test',
            unit_cost=Decimal('0.01')
        )
        
        # Get all unbilled
        unbilled = UsageLedger.get_unbilled()
        assert len(unbilled) == 2
        
        # Get unbilled for specific org
        unbilled_org1 = UsageLedger.get_unbilled(org_id='org-1')
        assert len(unbilled_org1) == 1
        assert unbilled_org1[0].org_id == 'org-1'


def test_usage_ledger_mark_billed(app):
    """Test marking entries as billed."""
    with app.app_context():
        # Create test entries
        entry1 = UsageLedger.record_usage(
            org_id='org-1',
            actor_id='key-1',
            route='/v1/test',
            unit_cost=Decimal('0.01')
        )
        
        entry2 = UsageLedger.record_usage(
            org_id='org-1',
            actor_id='key-1',
            route='/v1/test',
            unit_cost=Decimal('0.01')
        )
        
        # Mark as billed
        count = UsageLedger.mark_as_billed([entry1.id, entry2.id])
        assert count == 2
        
        # Verify billed_at is set
        db.session.refresh(entry1)
        db.session.refresh(entry2)
        assert entry1.billed_at is not None
        assert entry2.billed_at is not None
        
        # Verify no longer in unbilled
        unbilled = UsageLedger.get_unbilled(org_id='org-1')
        assert len(unbilled) == 0


def test_usage_ledger_to_dict(app):
    """Test dictionary conversion."""
    with app.app_context():
        entry = UsageLedger.record_usage(
            org_id='test-org',
            actor_id='test-key',
            route='/v1/test',
            unit_cost=Decimal('0.0100'),
            usage_units=5,
            agent_id='agent-123'
        )
        
        data = entry.to_dict()
        
        assert data['org_id'] == 'test-org'
        assert data['actor_id'] == 'test-key'
        assert data['route'] == '/v1/test'
        assert data['usage_units'] == 5
        assert data['unit_cost'] == 0.01
        assert data['total_cost'] == 0.05
        assert data['agent_id'] == 'agent-123'
        assert data['billed_at'] is None

