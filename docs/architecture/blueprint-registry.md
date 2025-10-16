# Blueprint Registration Helper

## Overview

The Blueprint Registration Helper provides a centralized, validated approach to registering Flask blueprints in the Brikk API Gateway. It addresses common issues with blueprint registration including:

- Missing error handling
- Inconsistent logging
- Difficulty debugging route registration issues
- No visibility into registered routes

## Components

### BlueprintRegistry Class

The main class for managing blueprint registration:

```python
from src.utils.blueprint_registry import create_blueprint_registry

# Create registry
registry = create_blueprint_registry(app)

# Register blueprints
registry.register(my_blueprint, url_prefix="/api")
```

**Features:**
- Automatic validation of blueprint instances
- Consistent error handling and logging
- Route inventory tracking
- Debug utilities for route inspection

### safe_register_blueprint Function

A standalone function for one-off blueprint registration:

```python
from src.utils.blueprint_registry import safe_register_blueprint

# Register with error handling
success = safe_register_blueprint(
    app,
    my_blueprint,
    url_prefix="/api",
    required=True  # Raise exception on failure
)
```

## Usage

### Basic Registration

```python
from src.utils.blueprint_registry import create_blueprint_registry

def register_all_blueprints(app):
    registry = create_blueprint_registry(app)
    
    # Register blueprints
    registry.register(health_bp, url_prefix="/")
    registry.register(api_bp, url_prefix="/api")
    registry.register(docs_bp)
    
    return registry
```

### With Error Handling

```python
# Optional blueprint - don't fail if import fails
try:
    from src.routes.dev_login import dev_bp
    registry.register(dev_bp, url_prefix="/api")
except Exception as e:
    app.logger.warning(f"Dev routes disabled: {e}")
```

### Debug Route Map

```python
# Print all registered routes (useful in development)
if app.debug:
    registry.print_route_map()
```

Output:
```
================================================================================
REGISTERED BLUEPRINTS AND ROUTES
================================================================================

Blueprint: health (prefix: /)
  Import: src.routes.health
  Routes: 3

Blueprint: api (prefix: /api)
  Import: src.routes.api
  Routes: 15

================================================================================
Total blueprints registered: 2
================================================================================
```

## Benefits

### 1. Consistent Error Handling

All blueprint registration errors are caught and logged consistently:

```python
# Before (PR-1 issue)
app.register_blueprint(my_bp)  # Silent failure or unclear error

# After
registry.register(my_bp)  # Clear error message with context
```

### 2. Better Debugging

The registry tracks all registered blueprints and their routes:

```python
# Get all registered blueprints
blueprints = registry.get_registered_blueprints()

for bp in blueprints:
    print(f"{bp['name']}: {bp['url_prefix']}")
```

### 3. Validation

Blueprints are validated before registration:

```python
# Invalid blueprint type
registry.register("not_a_blueprint")  # Returns False, logs error

# Valid blueprint
registry.register(valid_bp)  # Returns True, logs success
```

### 4. Centralized Management

All blueprint registration happens in one place, making it easier to:
- Understand the application's route structure
- Debug routing issues
- Add conditional blueprint registration
- Track which blueprints are loaded

## Integration with factory.py

The blueprint registry can be integrated into `factory.py`:

```python
def create_app() -> Flask:
    app = Flask(__name__)
    
    # ... app configuration ...
    
    # Register blueprints using the registry
    with app.app_context():
        registry = register_all_blueprints(app)
        
        # Optional: print route map in development
        if app.debug or os.getenv("BRIKK_LOG_ROUTES"):
            registry.print_route_map()
    
    return app
```

## Testing

The blueprint registry includes comprehensive tests:

```bash
pytest tests/test_blueprint_registry.py -v
```

Tests cover:
- Successful registration
- Invalid blueprint handling
- Custom URL prefixes
- Multiple blueprint registration
- Error handling (required vs optional)
- Route map printing

## Future Enhancements

Potential improvements for future PRs:

1. **Route Conflict Detection**: Warn about overlapping routes
2. **Performance Monitoring**: Track registration time
3. **Route Documentation**: Auto-generate route documentation
4. **Blueprint Dependencies**: Manage blueprint load order
5. **Hot Reload Support**: Enable blueprint reloading in development

## Related

- **PR-1**: Import Standardization - Created `src/infra` package
- **PR-2**: Blueprint Registration Helper (this document)
- **PR-4**: CI Guards - Will add validation for blueprint imports

## References

- [Flask Blueprints Documentation](https://flask.palletsprojects.com/en/latest/blueprints/)
- [Brikk Architecture Documentation](../README.md)

