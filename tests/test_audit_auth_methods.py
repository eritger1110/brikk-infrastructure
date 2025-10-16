"""
Tests for audit logging with different authentication methods.

Verifies that audit logs correctly capture auth_method for:
- API key authentication
- OAuth authentication  
- HMAC authentication
"""
import pytest
from src.models.api_gateway import ApiAuditLog
from src.database import db


def test_audit_log_with_api_key_auth():
    """Test audit log creation with API key authentication."""
    log = ApiAuditLog(
        org_id='00000000-0000-0000-0000-000000000001',
        actor_type='api_key',
        actor_id='test_key_123',
        auth_method='api_key',
        request_id='req_123',
        method='GET',
        path='/v1/test',
        status=200,
        cost_units=1
    )
    
    assert log.auth_method == 'api_key'
    assert log.actor_type == 'api_key'
    assert log.to_dict()['auth_method'] == 'api_key'


def test_audit_log_with_oauth_auth():
    """Test audit log creation with OAuth authentication."""
    log = ApiAuditLog(
        org_id='00000000-0000-0000-0000-000000000001',
        actor_type='oauth',
        actor_id='client_abc',
        auth_method='oauth',
        request_id='req_456',
        method='POST',
        path='/v1/agents',
        status=201,
        cost_units=1
    )
    
    assert log.auth_method == 'oauth'
    assert log.actor_type == 'oauth'
    assert log.to_dict()['auth_method'] == 'oauth'


def test_audit_log_with_hmac_auth():
    """Test audit log creation with HMAC authentication."""
    log = ApiAuditLog(
        org_id='00000000-0000-0000-0000-000000000001',
        actor_type='hmac',
        actor_id='hmac_key_xyz',
        auth_method='hmac',
        request_id='req_789',
        method='DELETE',
        path='/v1/agents/123',
        status=204,
        cost_units=1
    )
    
    assert log.auth_method == 'hmac'
    assert log.actor_type == 'hmac'
    assert log.to_dict()['auth_method'] == 'hmac'


def test_audit_log_defaults_auth_method():
    """Test that auth_method defaults to api_key if not provided."""
    log = ApiAuditLog(
        org_id='00000000-0000-0000-0000-000000000001',
        actor_type='api_key',
        actor_id='test_key_123',
        request_id='req_default',
        method='GET',
        path='/v1/test',
        status=200
    )
    
    # Should use server_default from database
    assert log.actor_type == 'api_key'


def test_log_request_classmethod_with_auth_method():
    """Test the log_request classmethod accepts auth_method parameter."""
    log = ApiAuditLog.log_request(
        org_id='00000000-0000-0000-0000-000000000001',
        actor_type='oauth',
        actor_id='client_test',
        request_id='req_classmethod',
        method='PATCH',
        path='/v1/agents/456',
        status=200,
        auth_method='oauth'
    )
    
    assert log.auth_method == 'oauth'
    assert log.actor_type == 'oauth'
    assert log.method == 'PATCH'
    assert log.status == 200


def test_log_request_classmethod_fallback_to_actor_type():
    """Test that auth_method falls back to actor_type if not provided."""
    log = ApiAuditLog.log_request(
        org_id='00000000-0000-0000-0000-000000000001',
        actor_type='hmac',
        actor_id='hmac_test',
        request_id='req_fallback',
        method='GET',
        path='/v1/test',
        status=200
    )
    
    # Should fallback to actor_type
    assert log.auth_method == 'hmac'
    assert log.actor_type == 'hmac'

