# API Deprecation Guide

## Overview

The Brikk API Gateway includes a comprehensive deprecation framework to support graceful API evolution. This guide explains how to use deprecation warnings and migrate to newer endpoints.

## Deprecation Headers

When you call a deprecated endpoint, you'll receive these headers:

```http
X-API-Deprecated: true
X-API-Deprecated-Since: 2025-10-16
X-API-Sunset-Date: 2026-01-01
X-API-Replacement: /api/v2/new-endpoint
Sunset: 2026-01-01
Warning: 299 - "Endpoint is deprecated and will be removed on 2026-01-01. Use /api/v2/new-endpoint instead" "2025-10-16"
```

### Header Descriptions

- **X-API-Deprecated**: Indicates the endpoint is deprecated (`true` or `false`)
- **X-API-Deprecated-Since**: ISO date when deprecation started
- **X-API-Sunset-Date**: ISO date when the endpoint will be removed (if scheduled)
- **X-API-Replacement**: Suggested replacement endpoint
- **Sunset**: RFC 8594 standard sunset header
- **Warning**: RFC 7234 standard warning header with detailed message

## Checking Deprecations

### List All Deprecations

Get a list of all deprecated endpoints:

```bash
curl https://api.getbrikk.com/api/deprecations
```

Response:

```json
{
  "deprecations": {
    "old_endpoint": {
      "deprecated_since": "2025-10-16",
      "sunset_date": "2026-01-01",
      "replacement": "/api/v2/new-endpoint",
      "message": "This endpoint is deprecated",
      "days_until_sunset": 77
    }
  },
  "count": 1,
  "message": "Check X-API-Deprecated headers in responses for real-time warnings"
}
```

## For API Developers

### Marking an Endpoint as Deprecated

Use the `@deprecated` decorator:

```python
from src.services.deprecation import deprecated
from flask import Blueprint, jsonify

bp = Blueprint('example', __name__)

@bp.route('/old-endpoint')
@deprecated(
    since='2025-10-16',
    sunset='2026-01-01',
    replacement='/api/v2/new-endpoint',
    message='This endpoint is deprecated due to security improvements'
)
def old_endpoint():
    return jsonify({'data': 'value'})
```

### Deprecation Timeline

1. **Announcement** (T+0): Add deprecation headers, update documentation
2. **Grace Period** (T+3 months): Endpoint remains fully functional
3. **Warning Period** (T+6 months): Add more prominent warnings
4. **Sunset** (T+12 months): Remove endpoint

## Best Practices

### For API Consumers

1. **Monitor Headers**: Check for `X-API-Deprecated` in all responses
2. **Plan Migration**: Use `days_until_sunset` to prioritize updates
3. **Test Replacements**: Validate replacement endpoints before sunset
4. **Update Dependencies**: Ensure all SDKs and clients are updated

### For API Developers

1. **Announce Early**: Give users at least 12 months notice
2. **Provide Alternatives**: Always specify a replacement endpoint
3. **Document Changes**: Update API docs and changelog
4. **Monitor Usage**: Track deprecated endpoint usage before removal

## Example Migration

### Old Endpoint (Deprecated)

```bash
curl -X GET https://api.getbrikk.com/api/v1/old-endpoint \
  -H "Authorization: Bearer $TOKEN"
```

### New Endpoint (Replacement)

```bash
curl -X GET https://api.getbrikk.com/api/v2/new-endpoint \
  -H "Authorization: Bearer $TOKEN"
```

## Support

If you need help migrating from a deprecated endpoint, contact support at support@getbrikk.com.

