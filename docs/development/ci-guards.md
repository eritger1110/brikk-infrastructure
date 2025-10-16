# CI Guards

## Overview

CI Guards are pre-deployment validation checks that run automatically in CI/CD
pipelines to catch common issues before they reach production. They were
introduced in PR-4 after the PR-1 production incident to prevent similar issues
in the future.

## What CI Guards Check

### 1. Critical Import Validation

Validates that all critical Python modules can be imported successfully:

- `src.infra.log` - Logging infrastructure
- `src.services.structured_logging` - Structured logging service
- `src.database` - Database connection
- `src.models` - Data models

**Purpose**: Prevents import errors like the one in PR-1 that broke production.

### 2. Python Syntax Validation

Checks all Python files in the `src/` directory for syntax errors using Python's
built-in AST parser.

**Purpose**: Catches basic syntax errors before deployment.

### 3. Route File Validation

Validates that all route files in `src/routes/` exist and can be imported.

**Purpose**: Ensures route blueprints are properly structured and importable.

### 4. Infrastructure Package Validation

Checks the `src/infra` package structure (created in PR-1):

- Directory exists
- `__init__.py` exists
- Expected modules are present
- Package can be imported
- Expected functions are exported

**Purpose**: Validates the infrastructure package refactoring from PR-1.

### 5. Environment Variable Documentation

Checks that required environment variables are documented in `.env.example`:

- File exists
- Critical variables are documented (`DATABASE_URL`, `SECRET_KEY`, `FLASK_ENV`)
- All variables are properly formatted

**Purpose**: Ensures deployment configuration is documented.

### 6. Utils Package Validation

Validates the `src/utils` package (created in PR-2):

- Directory exists
- `blueprint_registry.py` exists
- Blueprint registry classes and functions can be imported

**Purpose**: Validates the blueprint registry helper from PR-2.

## Running CI Guards

### Locally

Run the CI guards script directly:

```bash
python3.11 scripts/ci_guards.py
```

### In CI/CD

CI guards run automatically on every push and pull request via GitHub Actions:

```yaml
name: CI Guards
on: [push, pull_request]
jobs:
  ci-guards:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: python3.11 scripts/ci_guards.py
```

## Output

The script provides colorized output with clear success/failure indicators:

```text
Brikk Infrastructure - CI Guards
Running pre-deployment validation checks...

================================================================================
1. Critical Import Validation
================================================================================

✓ Import successful: src.infra.log
✓ Import successful: src.services.structured_logging
✓ Import successful: src.database
✓ Import successful: src.models

✓ All 4 critical imports validated

================================================================================
CI Guards Summary
================================================================================

✓ Critical Imports: PASSED
✓ Python Syntax: PASSED
✓ Route Files: PASSED
✓ Infrastructure Package: PASSED
✓ Environment Variables: PASSED
✓ Utils Package: PASSED

Results: 6/6 checks passed

✓ All CI guards passed! Safe to deploy.
```

## Exit Codes

- **0**: All checks passed
- **1**: One or more checks failed

## Adding New Checks

To add a new CI guard check:

1. Add a new function in `scripts/ci_guards.py`:

```python
def check_my_new_validation():
    """
    Description of what this check validates.
    """
    print_header("N. My New Validation")
    
    # Perform validation
    if validation_passes:
        print_success("Validation passed")
        return True
    else:
        print_error("Validation failed")
        return False
```

1. Add the check to the `checks` list in `main()`:

```python
checks = [
    # ... existing checks ...
    ("My New Validation", check_my_new_validation),
]
```

1. Update this documentation with the new check.

## Best Practices

### For Check Authors

- **Be specific**: Provide clear error messages
- **Be fast**: Checks should complete in seconds
- **Be deterministic**: Same code should always produce same result
- **Be informative**: Use warnings for non-critical issues

### For Developers

- **Run locally**: Test CI guards before pushing
- **Fix failures**: Don't ignore CI guard failures
- **Add checks**: Propose new checks for common issues
- **Keep updated**: Ensure checks stay relevant as code evolves

## Related

- **PR-1**: Import Standardization - Created `src/infra` package
- **PR-2**: Blueprint Registration Helper - Created `src/utils` package
- **PR-4**: CI Guards (this document)
- **Hotfix #96**: Fixed logging imports (production incident that inspired CI guards)

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Python AST Module](https://docs.python.org/3/library/ast.html)
- [Brikk Development Guide](../README.md)
