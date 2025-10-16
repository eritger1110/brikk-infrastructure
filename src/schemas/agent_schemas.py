# -*- coding: utf-8 -*-
"""
Agent Registry Request/Response Schemas (Phase 6 PR-I).

Provides Marshmallow schemas for validation and serialization.
"""
from marshmallow import Schema, fields, validate, ValidationError, EXCLUDE


class AgentCreateSchema(Schema):
    """Schema for creating a new agent."""
    class Meta:
        unknown = EXCLUDE
    
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(required=True, validate=validate.Length(min=1, max=1000))
    category = fields.Str(
        required=True,
        validate=validate.OneOf(['automation', 'analytics', 'communication', 'integration', 'other'])
    )
    capabilities = fields.List(fields.Str(), missing=[])
    oauth_client_id = fields.Str(required=False, allow_none=True)


class AgentUpdateSchema(Schema):
    """Schema for updating an existing agent."""
    class Meta:
        unknown = EXCLUDE
    
    name = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str(validate=validate.Length(min=1, max=1000))
    category = fields.Str(
        validate=validate.OneOf(['automation', 'analytics', 'communication', 'integration', 'other'])
    )
    capabilities = fields.List(fields.Str())
    active = fields.Bool()


class AgentResponseSchema(Schema):
    """Schema for agent response."""
    id = fields.Str()
    name = fields.Str()
    description = fields.Str()
    category = fields.Str()
    capabilities = fields.List(fields.Str())
    active = fields.Bool()
    oauth_client_id = fields.Str(allow_none=True)
    organization_id = fields.Int()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class AgentListResponseSchema(Schema):
    """Schema for agent list response."""
    agents = fields.List(fields.Nested(AgentResponseSchema))
    total = fields.Int()
    page = fields.Int()
    per_page = fields.Int()


class ErrorResponseSchema(Schema):
    """Schema for error responses."""
    error = fields.Str()
    message = fields.Str()
    request_id = fields.Str()
    details = fields.Dict(required=False)

