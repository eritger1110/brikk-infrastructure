# PR-3: OAuth2 Client Credentials Flow

## Overview

This PR implements OAuth2 client credentials flow for machine-to-machine authentication,
completing the unified auth system started in PR-2.

## What's Included

### 1. OAuth2 Service (`src/services/oauth2.py`)

JWT token generation and verification using python-jose:

- **Token Generation**: Creates JWT access tokens with HS256 algorithm
- **Token Verification**: Validates JWT signature, expiration, and claims
- **Client Secret Management**: Generates and verifies client secrets
- **Token Revocation**: Tracks and revokes tokens via database
- **Token Recording**: Optional tracking for audit and revocation

### 2. OAuth Routes (`src/routes/oauth.py`)

REST API for OAuth2 operations:

- `POST /oauth/token` - Token endpoint (client credentials grant)
- `POST /oauth/clients` - Create OAuth client
- `GET /oauth/clients` - List organization's clients
- `DELETE /oauth/clients/<client_id>` - Revoke client

### 3. Updated Unified Auth (`src/services/unified_auth.py`)

Bearer token authentication now fully implemented:

- Verifies JWT signature and expiration
- Checks token revocation status
- Populates Flask g with OAuth context
- Falls back to HMAC if no Bearer token

### 4. Dependencies (`requirements.txt`)

Added python-jose[cryptography]==3.3.0 for JWT operations

## OAuth2 Flow

```text
1. Register OAuth Client
   POST /oauth/clients
   {
     "name": "My App",
     "scopes": ["agents:read", "workflows:*"],
     "org_id": "uuid"
   }
   
   Response:
   {
     "client_id": "cli_abc123",
     "client_secret": "cs_live_..."  # SAVE THIS
   }

2. Request Access Token
   POST /oauth/token
   {
     "grant_type": "client_credentials",
     "client_id": "cli_abc123",
     "client_secret": "cs_live_...",
     "scope": "agents:read"  # Optional
   }
   
   Response:
   {
     "access_token": "eyJ...",
     "token_type": "Bearer",
     "expires_in": 3600,
     "scope": "agents:read"
   }

3. Use Access Token
   GET /api/v1/auth-test/agents-read
   Authorization: Bearer eyJ...
   
   Response:
   {
     "message": "You have agents:read permission",
     "auth_method": "oauth",
     "org_id": "uuid",
     "scopes": ["agents:read"]
   }
```

## JWT Token Structure

```json
{
  "iss": "brikk-api-gateway",
  "sub": "cli_abc123",
  "aud": "brikk-api",
  "exp": 1697400000,
  "iat": 1697396400,
  "nbf": 1697396400,
  "jti": "unique-token-id",
  "org_id": "uuid",
  "scopes": ["agents:read", "workflows:*"],
  "token_type": "access_token",
  "grant_type": "client_credentials"
}
```

## Token Lifecycle

- **Generation**: 60-minute expiration by default
- **Verification**: Signature, expiration, and revocation checked
- **Revocation**: Tokens can be revoked via database lookup
- **Tracking**: Optional recording in `oauth_tokens` table

## Security Features

1. **JWT Signing**: HS256 algorithm with secret key
2. **Token Expiration**: 1-hour default lifetime
3. **Revocation Support**: Database-backed token blacklist
4. **Client Secret Hashing**: SHA-256 hashing for storage
5. **Scope Validation**: Requested scopes validated against client's allowed scopes

## Testing

### Create OAuth Client

```bash
curl -X POST http://localhost:5000/oauth/clients \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Client",
    "scopes": ["agents:read", "agents:write"],
    "org_id": "<your_org_uuid>"
  }'
```

Response:

```json
{
  "client_id": "cli_abc123",
  "client_secret": "cs_live_a1b2c3...",
  "name": "Test Client",
  "scopes": ["agents:read", "agents:write"],
  "org_id": "uuid",
  "created_at": "2025-10-15T19:30:00Z",
  "is_active": true,
  "warning": "Save the client_secret now - it will not be shown again"
}
```

**Save the `client_secret` - it's only shown once!**

### Request Access Token

```bash
curl -X POST http://localhost:5000/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "cli_abc123",
    "client_secret": "cs_live_a1b2c3...",
    "scope": "agents:read"
  }'
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "agents:read"
}
```

### Use Bearer Token

```bash
curl http://localhost:5000/api/v1/auth-test/agents-read \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

Response:

```json
{
  "message": "You have agents:read permission",
  "auth_method": "oauth",
  "org_id": "uuid",
  "scopes": ["agents:read"]
}
```

## Environment Variables

- `JWT_SECRET_KEY` - Secret key for JWT signing (auto-generated if not set)

**Production**: Set `JWT_SECRET_KEY` to a strong random value in environment

```bash
export JWT_SECRET_KEY=$(openssl rand -base64 32)
```

## Migration Impact

- No new migrations required
- Uses tables from PR-1 (`oauth_clients`, `oauth_tokens`)
- Tables populated when clients are created

## Backward Compatibility

- ✅ Existing API key authentication unchanged
- ✅ Legacy HMAC authentication continues to work
- ✅ No breaking changes to existing routes
- ✅ New OAuth is additive only

## Comparison: API Keys vs OAuth

| Feature | API Keys | OAuth2 |
|---------|----------|--------|
| Use Case | Simple auth, long-lived | Machine-to-machine, short-lived |
| Lifetime | Permanent (until revoked) | 1 hour (renewable) |
| Format | `brk_live_*` | JWT Bearer token |
| Header | `X-API-Key` | `Authorization: Bearer` |
| Scopes | Static (set at creation) | Dynamic (requested per token) |
| Revocation | Instant (key disabled) | Database lookup required |

## Next Steps (PR-4)

- Implement tiered rate limiting per actor
- Add Prometheus metrics for auth events
- Create audit logging for all API requests
- Generate OpenAPI documentation

## Files Changed

- `src/services/oauth2.py` - New
- `src/routes/oauth.py` - New
- `src/services/unified_auth.py` - Modified (OAuth implementation)
- `src/factory.py` - Modified (blueprint registration)
- `requirements.txt` - Modified (added python-jose)
- `docs/api-gateway/PR3-OAUTH.md` - New

## Deployment Notes

- `JWT_SECRET_KEY` environment variable recommended for production
- If not set, a random key is generated (tokens won't survive restarts)
- python-jose dependency will be installed from requirements.txt
