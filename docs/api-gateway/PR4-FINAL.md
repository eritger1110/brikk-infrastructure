# PR-4: Rate Limiting, Telemetry, Audit Logging, and OpenAPI Docs

## Overview

Final PR to complete Stage 5 API Gateway implementation. Adds production-ready
features for monitoring, compliance, and developer experience.

## What Was Added

### 1. Tiered Rate Limiting

**File:** `src/services/rate_limiter.py`

- Per-actor rate limiting using Flask-Limiter
- Tiered limits based on actor tier:
  - FREE: 60 requests/minute
  - PRO: 600 requests/minute
  - ENT: 10,000 requests/minute
  - INTERNAL: 10,000 requests/minute (HMAC)
  - DEFAULT: 60 requests/minute (unauthenticated)
- Redis-backed for distributed rate limiting
- Graceful degradation if Redis unavailable
- Custom 429 responses with retry information
- X-RateLimit-* headers on all responses

### 2. Audit Logging

**File:** `src/services/audit_logger.py`

- Complete audit trail for all API requests
- Logs to `api_audit_log` table (from PR-1)
- Captures:
  - Request ID (X-Request-ID header)
  - Authentication details (org_id, actor_id, method)
  - Request details (endpoint, method, path, query params)
  - Client info (IP, User-Agent)
  - Response status and timing
- Middleware automatically logs all requests
- Non-blocking (doesn't fail requests if logging fails)

### 3. Gateway Metrics

**File:** `src/services/gateway_metrics.py`

Extends existing Prometheus metrics with API Gateway specific tracking:

- **Authentication metrics:**
  - `brikk_auth_requests_total` - Auth attempts by method and status
  - `brikk_auth_failures_total` - Auth failures by method and reason
  - `brikk_auth_latency_seconds` - Auth latency histogram
- **Rate limiting metrics:**
  - `brikk_rate_limit_exceeded_total` - Rate limit hits by tier/endpoint
  - `brikk_rate_limit_remaining` - Remaining requests gauge
- **Tier tracking:**
  - `brikk_requests_by_tier_total` - Requests by tier and endpoint
- **OAuth metrics:**
  - `brikk_oauth_tokens_issued_total` - Tokens issued by client
  - `brikk_oauth_token_verifications_total` - Token verifications
- **API key metrics:**
  - `brikk_api_key_usage_total` - Key usage by key_id and org_id

### 4. Telemetry Endpoint

**File:** `src/routes/telemetry.py`

SDK telemetry collection for monitoring and debugging:

- `POST /telemetry/events` - Collect events from SDKs
- `GET /telemetry/health` - Health check
- Accepts batch events with SDK metadata
- Logs events for monitoring (can be extended to database/analytics)
- No authentication required (public endpoint)

### 5. OpenAPI Documentation

**Files:**

- `src/static/openapi.json` - OpenAPI 3.0 specification
- `src/routes/docs.py` - Swagger UI routes
- `requirements.txt` - Added flask-swagger-ui

Features:

- Interactive API documentation at `/docs`
- Complete API reference with examples
- Authentication method documentation
- Try-it-out functionality
- Rate limit information
- Error response schemas

## Configuration

### Environment Variables

**Rate Limiting:**

- Redis URL configured in rate_limiter.py (default: `redis://localhost:6379`)
- Gracefully degrades if Redis unavailable

**Metrics:**

- `BRIKK_METRICS_ENABLED=true` (default) - Enable Prometheus metrics
- Metrics available at `/metrics`

**Audit Logging:**

- Always enabled
- Uses existing database connection
- Logs written to `api_audit_log` table

## Testing

### Rate Limiting

```bash
# Authenticated request (uses tier-based limit)
curl -H "X-API-Key: brk_live_..." https://api.getbrikk.com/api/v1/agents

# Check rate limit headers
HTTP/1.1 200 OK
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 599
X-RateLimit-Tier: PRO

# Exceed rate limit
# After 600 requests in 1 minute:
HTTP/1.1 429 Too Many Requests
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Please try again later.",
  "retry_after": "42 seconds",
  "limit": "600/minute",
  "tier": "PRO"
}
```

### Audit Logging

```bash
# Make any API request
curl -H "X-API-Key: brk_live_..." https://api.getbrikk.com/api/v1/agents

# Check database
SELECT * FROM api_audit_log ORDER BY created_at DESC LIMIT 1;

# Response includes request ID
HTTP/1.1 200 OK
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

### Metrics

```bash
# View Prometheus metrics
curl https://api.getbrikk.com/metrics

# Gateway-specific metrics
brikk_auth_requests_total{method="api_key",status="success"} 1234
brikk_rate_limit_exceeded_total{tier="FREE",endpoint="/api/v1/agents"} 5
brikk_requests_by_tier_total{tier="PRO",endpoint="/api/v1/workflows"} 890
brikk_oauth_tokens_issued_total{client_id="cli_abc123"} 42
```

### Telemetry

```bash
# Send telemetry events
curl -X POST https://api.getbrikk.com/telemetry/events \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "event_type": "api_call",
        "timestamp": "2025-10-15T19:30:00Z",
        "endpoint": "/api/v1/agents",
        "status_code": 200,
        "duration_ms": 150
      }
    ],
    "sdk_info": {
      "name": "brikk-python-sdk",
      "version": "1.0.0"
    }
  }'

# Response
HTTP/1.1 202 Accepted
{
  "message": "Events received",
  "events_count": 1
}
```

### OpenAPI Docs

```bash
# View interactive documentation
open https://api.getbrikk.com/docs

# Download OpenAPI spec
curl https://api.getbrikk.com/static/openapi.json
```

## Safety

- All features are additive and non-breaking
- Rate limiting gracefully degrades if Redis unavailable
- Audit logging doesn't fail requests if logging fails
- Metrics are optional (can be disabled)
- Telemetry endpoint is public (no auth required)
- OpenAPI docs are read-only

## Dependencies Added

- `flask-swagger-ui==4.11.1` - Swagger UI for OpenAPI docs

## Next Steps After Merge

1. **Configure Redis** - For distributed rate limiting in production
2. **Monitor Metrics** - Set up Prometheus/Grafana dashboards
3. **Review Audit Logs** - Verify compliance requirements
4. **Test Documentation** - Ensure `/docs` works correctly
5. **SDK Integration** - Update SDKs to send telemetry

## Stage 5 Complete

With PR-4 merged, Stage 5 (API Gateway) is complete:

- Authentication (API Keys, OAuth2, HMAC)
- Authorization (Scope-based access control)
- Rate Limiting (Tiered per actor)
- Monitoring (Prometheus metrics)
- Audit Logging (Compliance trail)
- Telemetry (SDK monitoring)
- Documentation (OpenAPI/Swagger)

Brikk is now production-ready for external developers!
