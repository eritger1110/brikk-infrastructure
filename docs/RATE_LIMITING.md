# Rate Limiting Configuration

Brikk's coordination API includes Redis-based sliding window rate limiting with per-organization or per-API-key scoping.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BRIKK_RLIMIT_ENABLED` | `false` | Enable/disable rate limiting |
| `BRIKK_RLIMIT_PER_MIN` | `60` | Base requests per minute |
| `BRIKK_RLIMIT_BURST` | `20` | Additional burst capacity |
| `BRIKK_RLIMIT_SCOPE` | `org` | Scope: `org` or `key` |

### Total Limit Calculation

```
Total Limit = BRIKK_RLIMIT_PER_MIN + BRIKK_RLIMIT_BURST
```

**Example**: With defaults (60 + 20 = 80 requests per minute)

## Scoping Options

### Organization Scoping (`BRIKK_RLIMIT_SCOPE=org`)
- Rate limits apply per organization
- All API keys within an organization share the same limit
- Useful for tenant-based limiting

### API Key Scoping (`BRIKK_RLIMIT_SCOPE=key`)
- Rate limits apply per individual API key
- Each API key has its own independent limit
- Useful for fine-grained control

## Rate Limit Headers

All responses include standard rate limit headers:

```http
X-RateLimit-Limit: 80
X-RateLimit-Remaining: 75
X-RateLimit-Reset: 1640995200
```

### 429 Rate Limited Response

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 80
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640995200
Retry-After: 45
Content-Type: application/json

{
  "code": "rate_limited",
  "message": "Rate limit exceeded",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Sliding Window Algorithm

The rate limiter uses a Redis-based sliding window:

1. **Window Size**: 60 seconds (1 minute)
2. **Granularity**: Per-second timestamps
3. **Cleanup**: Automatic removal of expired entries
4. **Atomicity**: Redis pipeline for consistent operations

### Redis Keys

- **Organization scope**: `rlimit:org:{organization_id}`
- **API key scope**: `rlimit:key:{api_key_id}`
- **Anonymous scope**: `rlimit:anonymous` (fallback)

## Graceful Degradation

When Redis is unavailable:
- Rate limiting is automatically disabled
- All requests are allowed through
- No 429 errors are returned
- Errors are logged for monitoring

## Integration with Authentication

Rate limiting is applied **after** HMAC authentication:

```
Request → Guards → HMAC Auth → Rate Limit → Idempotency → Validation
```

This ensures:
- Only authenticated requests consume rate limit quota
- Rate limits are scoped to authenticated entities
- Invalid requests don't affect rate limits

## Monitoring and Debugging

### Health Check

```bash
curl -X GET /api/v1/coordination/health
```

Response includes rate limiter status:

```json
{
  "status": "healthy",
  "service": "coordination-api",
  "features": {
    "rate_limiting": true,
    "redis_connected": true
  }
}
```

### Usage Statistics

Rate limiter provides usage statistics for monitoring:

```python
from src.services.rate_limit import get_rate_limiter

rate_limiter = get_rate_limiter()
usage = rate_limiter.get_current_usage("rlimit:org:example-org")
```

## Best Practices

### Production Configuration

```bash
# Enable rate limiting
BRIKK_RLIMIT_ENABLED=true

# Conservative limits for production
BRIKK_RLIMIT_PER_MIN=100
BRIKK_RLIMIT_BURST=50

# Organization-based scoping
BRIKK_RLIMIT_SCOPE=org
```

### Development Configuration

```bash
# Disable rate limiting for development
BRIKK_RLIMIT_ENABLED=false

# Or use generous limits
BRIKK_RLIMIT_PER_MIN=1000
BRIKK_RLIMIT_BURST=500
```

### Redis Configuration

Ensure Redis is properly configured:

```bash
# Redis connection
REDIS_URL=redis://localhost:6379/0

# For production, use Redis Cluster or Sentinel
REDIS_URL=redis://redis-cluster:6379/0
```

## Troubleshooting

### Common Issues

1. **Rate limits too restrictive**
   - Increase `BRIKK_RLIMIT_PER_MIN` or `BRIKK_RLIMIT_BURST`
   - Consider switching from `org` to `key` scoping

2. **Redis connection failures**
   - Check Redis connectivity
   - Verify `REDIS_URL` configuration
   - Monitor Redis logs

3. **Unexpected 429 responses**
   - Check current usage with health endpoint
   - Verify scoping configuration
   - Review authentication context

### Debugging Commands

```bash
# Check Redis connectivity
redis-cli ping

# Monitor rate limit keys
redis-cli keys "rlimit:*"

# Check specific scope usage
redis-cli zcard "rlimit:org:example-org"
```

## Security Considerations

- Rate limits are enforced after authentication
- Unauthenticated requests don't consume quota
- Redis keys include scope identifiers for isolation
- Graceful degradation prevents DoS on Redis failures
