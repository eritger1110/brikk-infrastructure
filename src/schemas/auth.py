# -*- coding: utf-8 -*-
"""
Authentication schemas for API key management and HMAC validation.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
import re


class CreateOrganizationRequest(BaseModel):
    """Schema for creating a new organization."""
    name: str = Field(..., min_length=1, max_length=255,
                      description="Organization name")
    slug: str = Field(..., min_length=1, max_length=100,
                      description="URL-friendly organization identifier")
    description: Optional[str] = Field(
        None, max_length=1000, description="Organization description")
    contact_email: Optional[str] = Field(
        None, description="Primary contact email")
    contact_name: Optional[str] = Field(
        None, max_length=255, description="Primary contact name")
    monthly_request_limit: int = Field(
        10000, ge=1, le=1000000, description="Monthly API request limit")

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v):
        """Validate slug format (alphanumeric, hyphens, underscores only)."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                'Slug must contain only alphanumeric characters, hyphens, and underscores')
        return v.lower()

    @field_validator('contact_email')
    @classmethod
    def validate_email(cls, v):
        """Basic email validation."""
        if v and not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
            raise ValueError('Invalid email format')
        return v


class CreateAgentRequest(BaseModel):
    """Schema for creating a new agent."""
    agent_id: str = Field(..., min_length=1, max_length=255,
                          description="Unique agent identifier")
    name: str = Field(..., min_length=1, max_length=255,
                      description="Agent display name")
    description: Optional[str] = Field(
        None, max_length=1000, description="Agent description")
    agent_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Agent type (e.g., coordinator, worker)")
    capabilities: Optional[str] = Field(
        None, description="JSON string of agent capabilities")
    endpoint_url: Optional[str] = Field(
        None, max_length=500, description="Agent callback URL")

    @field_validator('agent_id')
    @classmethod
    def validate_agent_id(cls, v):
        """Validate agent ID format."""
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError(
                'Agent ID must contain only alphanumeric characters, dots, hyphens, and underscores')
        return v


class CreateApiKeyRequest(BaseModel):
    """Schema for creating a new API key."""
    name: str = Field(..., min_length=1, max_length=255,
                      description="API key name")
    description: Optional[str] = Field(
        None, max_length=1000, description="API key description")
    agent_id: Optional[int] = Field(
        None, description="Optional agent ID to scope the key")
    expires_days: Optional[int] = Field(
        None, ge=1, le=3650, description="Expiration in days (max 10 years)")
    scopes: Optional[List[str]] = Field(
        None, description="List of allowed scopes")
    requests_per_minute: int = Field(
        100, ge=1, le=10000, description="Rate limit per minute")
    requests_per_hour: int = Field(
        1000, ge=1, le=100000, description="Rate limit per hour")

    @field_validator('scopes')
    @classmethod
    def validate_scopes(cls, v):
        """Validate scopes format."""
        if v:
            allowed_scopes = [
                'coordination:read',
                'coordination:write',
                'agents:read',
                'agents:write',
                'admin']
            for scope in v:
                if scope not in allowed_scopes:
                    raise ValueError(
                        f'Invalid scope: {scope}. Allowed: {", ".join(allowed_scopes)}')
        return v


class RotateApiKeyRequest(BaseModel):
    """Schema for rotating an API key."""
    key_id: str = Field(..., description="API key ID to rotate")


class DisableApiKeyRequest(BaseModel):
    """Schema for disabling an API key."""
    key_id: str = Field(..., description="API key ID to disable")
    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for disabling")


class ApiKeyResponse(BaseModel):
    """Schema for API key response."""
    id: int
    key_id: str
    key_prefix: str
    organization_id: int
    organization_name: Optional[str]
    agent_id: Optional[int]
    agent_name: Optional[str]
    name: str
    description: Optional[str]
    scopes: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str
    expires_at: Optional[str]
    last_used_at: Optional[str]
    total_requests: int
    failed_requests: int
    success_rate: float
    requests_per_minute: int
    requests_per_hour: int
    is_valid: bool


class ApiKeyWithSecretResponse(ApiKeyResponse):
    """Schema for API key response including secret (only during creation)."""
    secret: str = Field(...,
                        description="HMAC secret (only provided during creation)")


class OrganizationResponse(BaseModel):
    """Schema for organization response."""
    id: int
    name: str
    slug: str
    description: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str
    contact_email: Optional[str]
    contact_name: Optional[str]
    monthly_request_limit: int
    current_month_requests: int
    agent_count: int
    api_key_count: int


class AgentResponse(BaseModel):
    """Schema for agent response."""
    id: int
    agent_id: str
    name: str
    description: Optional[str]
    organization_id: int
    organization_name: Optional[str]
    agent_type: Optional[str]
    capabilities: Optional[str]
    endpoint_url: Optional[str]
    is_active: bool
    last_seen_at: Optional[str]
    created_at: str
    updated_at: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    active_api_keys: int


class AuthenticationContext(BaseModel):
    """Schema for authentication context."""
    organization_id: int
    agent_id: Optional[int]
    key_id: str
    scopes: List[str]
    authenticated_at: str
    request_id: str


class HMACValidationRequest(BaseModel):
    """Schema for HMAC validation request (internal use)."""
    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="Request path")
    timestamp: str = Field(..., description="RFC3339 timestamp")
    body_hash: str = Field(..., description="SHA-256 hash of request body")
    signature: str = Field(..., description="HMAC signature")
    message_id: Optional[str] = Field(
        None, description="Message ID from request body")


class IdempotencyCheckRequest(BaseModel):
    """Schema for idempotency check request."""
    api_key_id: str = Field(..., description="API key ID")
    body_hash: str = Field(..., description="SHA-256 hash of request body")
    custom_idempotency_key: Optional[str] = Field(
        None, description="Custom idempotency key from header")


class IdempotencyResponse(BaseModel):
    """Schema for idempotency check response."""
    should_process: bool = Field(...,
                                 description="Whether to process the request")
    cached_response: Optional[Dict[str, Any]] = Field(
        None, description="Cached response data if available")
    status_code: Optional[int] = Field(
        None, description="Cached response status code")
    conflict_type: Optional[str] = Field(
        None, description="Type of conflict if any")


class AuthErrorResponse(BaseModel):
    """Schema for authentication error responses."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    request_id: str = Field(..., description="Request ID for tracking")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details")


class AuthSuccessResponse(BaseModel):
    """Schema for successful authentication responses."""
    status: str = Field("authenticated", description="Authentication status")
    organization_id: int = Field(...,
                                 description="Authenticated organization ID")
    agent_id: Optional[int] = Field(None, description="Authenticated agent ID")
    key_id: str = Field(..., description="API key ID used")
    scopes: List[str] = Field(..., description="Available scopes")
    request_id: str = Field(..., description="Request ID for tracking")


class RateLimitInfo(BaseModel):
    """Schema for rate limit information."""
    requests_per_minute: int
    requests_per_hour: int
    current_minute_requests: int
    current_hour_requests: int
    reset_minute: str
    reset_hour: str
    is_limited: bool


class ApiKeyStatsResponse(BaseModel):
    """Schema for API key statistics."""
    key_id: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    last_used_at: Optional[str]
    requests_today: int
    requests_this_hour: int
    average_requests_per_day: float
    rate_limit_info: RateLimitInfo
