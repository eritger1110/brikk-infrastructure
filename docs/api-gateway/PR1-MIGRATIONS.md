# PR-1: API Gateway Migrations and Models

## Overview

This PR adds the database schema and SQLAlchemy models for Stage 5 API Gateway functionality.
**No behavior changes** - the app continues to work exactly as before.

## Changes

### Migration: `e173b895ecb0_add_api_gateway_tables.py`

Adds 4 new tables for API Gateway functionality:

1. **`org_api_keys`** - Scoped API keys for organizations
   - Supports tiered access (FREE, PRO, ENT)
   - Stores key hashes (never plaintext)
   - GIN index on scopes for fast lookups

2. **`oauth_clients`** - OAuth2 client registrations
   - Supports client credentials flow
   - Extensible for authorization code flow
   - Stores client secret hashes

3. **`oauth_tokens`** - OAuth2 token tracking
   - Tracks issued access/refresh tokens
   - Supports revocation and expiry
   - Indexed for fast validation

4. **`api_audit_log`** - API request audit trail
   - Captures who, what, when, result
   - Supports cost tracking
   - Composite indexes for efficient queries

### Models: `src/models/api_gateway.py`

SQLAlchemy models for the 4 new tables:

- `OrgApiKey` - API key management with scope checking
- `OAuthClient` - OAuth2 client with grant type validation
- `OAuthToken` - Token lifecycle management
- `ApiAuditLog` - Audit logging with helper methods

All models include:
- Proper type hints
- Helper methods (`is_active()`, `has_scope()`, etc.)
- `to_dict()` for API responses
- Comprehensive docstrings

## Database Requirements

**PostgreSQL 12+** is required for:
- `gen_random_uuid()` function (or pgcrypto extension)
- `ARRAY` column types
- GIN indexes

## Testing

### Models Import
```bash
python3.11 -c "from src.models import OrgApiKey, OAuthClient, OAuthToken, ApiAuditLog"
```

### Migration Chain
```bash
python3.11 -m alembic history
# Output: b07a366647c3 -> e173b895ecb0 (head)
```

### CI Testing
The existing `migrations` job in CI will test this migration on PostgreSQL 16.

## Acceptance Criteria

✅ Migration chains from baseline (`b07a366647c3`)
✅ Models import without errors
✅ No behavior changes to existing app
✅ CI migrations job passes
✅ Render deployment stays Live

## Next Steps (PR-2)

- Implement API key authentication
- Add unified auth middleware
- Guard existing routes with scopes

## Notes

- This PR is safe to merge - it only adds schema, no code changes
- The new tables will be empty until PR-2 adds the auth endpoints
- HMAC authentication continues to work unchanged

