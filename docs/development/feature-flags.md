# Feature Flags System

## Overview

The feature flags system allows you to enable or disable features dynamically without code deployments. This is essential for:

- **Safe rollouts**: Gradually enable features for a subset of users
- **A/B testing**: Test different features with different user groups
- **Quick toggles**: Disable problematic features instantly in production
- **Development**: Enable experimental features only in development

## Quick Start

### Check if a feature is enabled

```python
from src.utils.feature_flags import is_enabled, FeatureFlag

if is_enabled(FeatureFlag.AGENT_REGISTRY):
    # Feature is enabled
    register_agent()
```

### Set a feature flag (requires Redis)

```python
from src.utils.feature_flags import set_flag, FeatureFlag

# Enable a feature
set_flag(FeatureFlag.AGENT_MARKETPLACE, True)

# Enable with TTL (auto-disable after 1 hour)
set_flag(FeatureFlag.DEBUG_MODE, True, ttl=3600)
```

### Get all flags

```python
from src.utils.feature_flags import get_all_flags

flags = get_all_flags()
# Returns: {"agent_registry": True, "agent_marketplace": False, ...}
```

## Configuration

### Environment Variables

Override any flag using environment variables:

```bash
# Enable a feature
export FEATURE_FLAG_AGENT_MARKETPLACE=true

# Disable a feature
export FEATURE_FLAG_AGENT_REGISTRY=false
```

Accepted values for enabled: `true`, `1`, `yes`, `on`

Accepted values for disabled: `false`, `0`, `no`, `off`

### Redis (Optional)

For dynamic runtime configuration, initialize with Redis:

```python
from src.utils.feature_flags import init_feature_flags
import redis

redis_client = redis.from_url(os.getenv("REDIS_URL"))
init_feature_flags(redis_client)
```

## Priority Order

When checking if a feature is enabled, the system checks in this order:

1. **Environment variable** (highest priority)
1. **Redis value** (if Redis is configured)
1. **Default value** (defined in code)

This means environment variables always win, allowing you to force-enable or force-disable features regardless of Redis configuration.

## Available Flags

### Phase 6: Agent Registry

- `agent_registry` - Agent registration and management (default: enabled)
- `agent_discovery` - Agent discovery functionality (default: enabled)
- `agent_versioning` - Agent version management (default: enabled)

### Phase 7: Future Features

- `agent_marketplace` - Agent marketplace (default: disabled)
- `agent_analytics` - Agent analytics and insights (default: disabled)

### Infrastructure

- `rate_limiting` - API rate limiting (default: enabled)
- `caching` - Response caching (default: enabled)
- `metrics` - Metrics collection (default: enabled)

### Development

- `debug_mode` - Debug mode (default: disabled)
- `verbose_logging` - Verbose logging (default: disabled)

## Adding New Flags

### 1. Define the flag

Edit `src/utils/feature_flags.py`:

```python
class FeatureFlag(str, Enum):
    # ... existing flags ...
    MY_NEW_FEATURE = "my_new_feature"
```

### 2. Set default value

```python
DEFAULT_FLAGS = {
    # ... existing defaults ...
    FeatureFlag.MY_NEW_FEATURE: False,  # Disabled by default
}
```

### 3. Use the flag

```python
from src.utils.feature_flags import is_enabled, FeatureFlag

if is_enabled(FeatureFlag.MY_NEW_FEATURE):
    # Your new feature code
    pass
```

## API Endpoints

### List all feature flags

```bash
GET /api/v1/feature-flags
```

Response:

```json
{
  "success": true,
  "flags": {
    "agent_registry": true,
    "agent_marketplace": false,
    ...
  },
  "count": 10
}
```

### Get a specific flag

```bash
GET /api/v1/feature-flags/agent_registry
```

Response:

```json
{
  "success": true,
  "flag": "agent_registry",
  "enabled": true
}
```

### Update a flag (requires Redis)

```bash
PUT /api/v1/feature-flags/agent_marketplace
Content-Type: application/json

{
  "enabled": true,
  "ttl": 3600
}
```

Response:

```json
{
  "success": true,
  "flag": "agent_marketplace",
  "enabled": true,
  "ttl": 3600
}
```

## Best Practices

### 1. Use descriptive flag names

```python
# Good
FeatureFlag.AGENT_MARKETPLACE

# Bad
FeatureFlag.FEATURE_1
```

### 2. Set safe defaults

New features should be disabled by default:

```python
DEFAULT_FLAGS = {
    FeatureFlag.NEW_EXPERIMENTAL_FEATURE: False,  # Safe default
}
```

### 3. Document flag purpose

Add comments explaining what each flag controls:

```python
class FeatureFlag(str, Enum):
    # Enables the new agent marketplace feature (Phase 7)
    AGENT_MARKETPLACE = "agent_marketplace"
```

### 4. Clean up old flags

Remove flags for features that are fully rolled out:

```python
# Before (feature flag)
if is_enabled(FeatureFlag.SOME_FEATURE):
    new_behavior()
else:
    old_behavior()

# After (feature fully rolled out)
new_behavior()  # Flag removed, feature always on
```

### 5. Use TTL for temporary changes

When enabling a feature temporarily:

```python
# Enable debug mode for 1 hour
set_flag(FeatureFlag.DEBUG_MODE, True, ttl=3600)
```

## Testing

### Test with environment variables

```python
def test_feature_with_flag_enabled(monkeypatch):
    monkeypatch.setenv("FEATURE_FLAG_MY_FEATURE", "true")
    # Your test code
```

### Test with mock Redis

```python
from unittest.mock import Mock

def test_feature_with_redis():
    mock_redis = Mock()
    mock_redis.get.return_value = b"true"
    
    init_feature_flags(mock_redis)
    # Your test code
```

## Production Usage

### Gradual Rollout

1. Deploy code with feature disabled by default
1. Enable for internal testing via environment variable
1. Enable for beta users via Redis
1. Enable for all users via Redis
1. Update default to enabled and remove flag

### Emergency Disable

If a feature causes issues in production:

```bash
# Option 1: Via Redis (instant)
redis-cli SET feature_flag:problematic_feature false

# Option 2: Via environment variable (requires restart)
export FEATURE_FLAG_PROBLEMATIC_FEATURE=false
# Restart application
```

### Monitoring

Monitor feature flag usage:

```python
from src.utils.feature_flags import get_all_flags
import logging

logger = logging.getLogger(__name__)

# Log current flag states on startup
flags = get_all_flags()
logger.info(f"Feature flags: {flags}")
```

## Troubleshooting

### Flag not taking effect

Check priority order:

1. Is there an environment variable set?
1. Is Redis configured and reachable?
1. Is the default value correct?

### Redis errors

If Redis is unavailable, the system falls back to environment variables and defaults. Check logs for warnings.

### Flag not found

Ensure the flag is defined in `FeatureFlag` enum:

```python
class FeatureFlag(str, Enum):
    YOUR_FLAG = "your_flag"  # Must be defined here
```

## Related Documentation

- [Environment Variables](../operations/environment-variables.md)
- [Redis Configuration](../operations/redis.md)
- [API Documentation](../api/README.md)

