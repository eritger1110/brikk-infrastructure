# -*- coding: utf-8 -*-
"""
Trust Layer Schemas (Phase 7 PR-1).

Marshmallow schemas for reputation, attestations, and risk events.
"""
from marshmallow import Schema, fields, validate, EXCLUDE


class ReputationResponseSchema(Schema):
    """Schema for reputation response."""
    class Meta:
        unknown = EXCLUDE
    
    subject_type = fields.Str(required=True)
    subject_id = fields.Str(required=True)
    score = fields.Int(required=True)
    score_bucket = fields.Str(required=True)  # e.g., "80-90" for privacy
    window = fields.Str(required=True)
    top_factors = fields.List(fields.Dict(), required=True)
    last_updated = fields.DateTime(required=True)


class AttestationCreateSchema(Schema):
    """Schema for creating an attestation."""
    class Meta:
        unknown = EXCLUDE
    
    subject_type = fields.Str(
        required=True,
        validate=validate.OneOf(['org', 'agent'])
    )
    subject_id = fields.Str(required=True, validate=validate.Length(min=1, max=36))
    scopes = fields.List(
        fields.Str(validate=validate.Length(min=1, max=50)),
        required=True,
        validate=validate.Length(min=1)
    )
    weight = fields.Int(
        load_default=1,
        validate=validate.Range(min=1, max=10)
    )
    note = fields.Str(validate=validate.Length(max=500))


class AttestationResponseSchema(Schema):
    """Schema for attestation response."""
    class Meta:
        unknown = EXCLUDE
    
    id = fields.Str(required=True)
    issuer_org = fields.Str(required=True)
    subject_type = fields.Str(required=True)
    subject_id = fields.Str(required=True)
    scopes = fields.List(fields.Str(), required=True)
    weight = fields.Int(required=True)
    note = fields.Str(allow_none=True)
    created_at = fields.DateTime(required=True)


class AttestationListResponseSchema(Schema):
    """Schema for attestation list response."""
    class Meta:
        unknown = EXCLUDE
    
    attestations = fields.List(fields.Nested(AttestationResponseSchema))
    total = fields.Int()
    subject_type = fields.Str()
    subject_id = fields.Str()


class RiskEventSchema(Schema):
    """Schema for risk event."""
    class Meta:
        unknown = EXCLUDE
    
    id = fields.Str(required=True)
    org_id = fields.Str(required=True)
    actor_id = fields.Str(allow_none=True)
    type = fields.Str(required=True)
    severity = fields.Str(required=True, validate=validate.OneOf(['low', 'med', 'high']))
    meta = fields.Dict(allow_none=True)
    created_at = fields.DateTime(required=True)


class ReputationRecomputeRequestSchema(Schema):
    """Schema for reputation recompute request."""
    class Meta:
        unknown = EXCLUDE
    
    window = fields.Str(
        load_default='30d',
        validate=validate.OneOf(['7d', '30d', '90d'])
    )
    subject_type = fields.Str(validate=validate.OneOf(['org', 'agent']))
    subject_id = fields.Str(validate=validate.Length(min=1, max=36))

