# PR-2: Scoped API Keys + Unified Auth

## Overview

This PR implements the authentication layer for the API Gateway, supporting multiple authentication methods with scope-based authorization.

## What's Included

### 1. API Key Utilities (`src/services/api_key_utils.py`)

- **Key Generation**: Creates high-entropy API keys with prefixes
  - Live keys: `brk_live_<64_hex_chars>`
  - Test keys: `brk_test_<64_hex_chars>`
- **Hashing**: SHA-256 hashing for secure storage
- **Verification**: Constant-time comparison to prevent timing attacks

### 2. Unified Auth Middleware (`src/services/unified_auth.py`)

Supports three authentication methods in priority order:

1. **API Key** (via `X-API-Key` header)
   - Looks up key in `org_api_keys` table
   - Validates key is active (not revoked)
   - Populates Flask g with org_id, scopes, tier

2. **OAuth2 Bearer** (via `Authorization: Bearer` header)
   - Placeholder for PR-3 implementation
   - Returns 501 Not Implemented for now

3. **Legacy HMAC** (via `X-Brikk-*` headers)
   - Backward compatible with existing integrations
   - Delegates to existing `HMACSecurityService`
   - Grants full access (`*` scope) for compatibility

### 3. API Key Management (`src/routes/api_keys.py`)

REST API for managing API keys:

- `POST /api/v1/keys` - Create new API key
- `GET /api/v1/keys` - List organization's keys
- `GET /api/v1/keys/<key_id>` - Get key details
- `DELETE /api/v1/keys/<key_id>` - Revoke key

**Note**: Currently requires `org_id` in request for testing. Will use authenticated session in PR-3.

### 4. Test Routes (`src/routes/auth_test.py`)

Demonstration endpoints for testing auth flows:

- `/api/v1/auth-test/public` - No auth required
- `/api/v1/auth-test/authenticated` - Requires any valid auth
- `/api/v1/auth-test/agents-read` - Requires `agents:read` scope
- `/api/v1/auth-test/agents-write` - Requires `agents:write` scope
- `/api/v1/auth-test/admin` - Requires `admin:*` scope

## Authentication Flow

```
Request with X-API-Key header
    ↓
Unified Auth Middleware
    ↓
1. Try API Key auth
    - Hash provided key
    - Look up in org_api_keys table
    - Check if active
    - Populate Flask g
    ↓
2. Try OAuth (if no API key)
    - Returns 501 for now
    ↓
3. Try HMAC (if no OAuth)
    - Verify signature
    - Grant full access
    ↓
@require_auth decorator
    - Check if authenticated
    - Verify required scopes
    - Allow or deny (403)
```

## Scope System

Scopes follow a hierarchical pattern:

- `*` - Full access (wildcard)
- `agents:*` - All agent operations
- `agents:read` - Read agent data only
- `agents:write` - Create/update agents
- `workflows:*` - All workflow operations
- `admin:*` - Admin operations

The `@require_auth(scopes=[...])` decorator accepts a list of acceptable scopes. If the authenticated actor has ANY of the required scopes, access is granted.

## Rate Limit Tiers

API keys have a `tier` field for rate limiting (implemented in PR-4):

- `FREE` - 60 requests/minute
- `PRO` - 600 requests/minute
- `ENT` - Negotiated limits

## Testing

### Create an API Key

```bash
curl -X POST http://localhost:5000/api/v1/keys \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Key",
    "scopes": ["agents:read", "agents:write"],
    "tier": "PRO",
    "is_test": false,
    "org_id": "<your_org_uuid>"
  }'
```

Response:

```json
{
  "api_key": "brk_live_a1b2c3...",
  "id": "uuid",
  "org_id": "uuid",
  "name": "Test Key",
  "scopes": ["agents:read", "agents:write"],
  "tier": "PRO",
  "created_at": "2025-10-15T19:30:00Z",
  "is_active": true,
  "key_prefix": "brk_live_a1b2"
}
```

**Save the `api_key` value - it's only shown once!**

### Test Authentication

```bash
# Public endpoint (no auth)
curl http://localhost:5000/api/v1/auth-test/public

# Authenticated endpoint
curl http://localhost:5000/api/v1/auth-test/authenticated \
  -H "X-API-Key: brk_live_a1b2c3..."

# Scoped endpoint (requires agents:read)
curl http://localhost:5000/api/v1/auth-test/agents-read \
  -H "X-API-Key: brk_live_a1b2c3..."

# Should return 403 if key doesn't have admin:* scope
curl http://localhost:5000/api/v1/auth-test/admin \
  -H "X-API-Key: brk_live_a1b2c3..."
```

## Migration Impact

- Uses tables created in PR-1 (`org_api_keys`, `oauth_clients`, `oauth_tokens`, `api_audit_log`)
- No new migrations required
- Tables remain empty until keys are created via API

## Backward Compatibility

- Existing HMAC authentication continues to work unchanged
- Legacy API keys (from `api_keys` table) still function
- New scoped keys (from `org_api_keys` table) coexist with legacy system
- No breaking changes to existing routes

## Security Considerations

1. **Key Storage**: API keys are hashed with SHA-256 before storage
2. **Constant-Time Comparison**: Prevents timing attacks during verification
3. **Scope Enforcement**: Routes protected by `@require_auth` check scopes
4. **Revocation**: Keys can be revoked instantly via DELETE endpoint
5. **High Entropy**: 256-bit random keys (64 hex characters)

## Next Steps (PR-3)

- Implement OAuth2 client credentials flow
- Add `/oauth/token` endpoint
- JWT token generation and verification
- Replace temporary `org_id` parameter with authenticated session
- Update API key management to use OAuth for authentication

## Files Changed

- `src/services/api_key_utils.py` - New
- `src/services/unified_auth.py` - New
- `src/routes/api_keys.py` - New
- `src/routes/auth_test.py` - New
- `src/factory.py` - Modified (blueprint registration)
- `docs/api-gateway/PR2-AUTH.md` - New

## Deployment Notes

- No environment variables required
- No configuration changes needed
- App boots with no behavior changes
- New endpoints available but optional
- Existing auth methods continue to work
