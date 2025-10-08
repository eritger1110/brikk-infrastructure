# Dependabot Configuration

This document describes the Dependabot configuration for the Brikk Infrastructure repository.

## Overview

Dependabot is configured to automatically manage dependency updates with intelligent grouping and auto-merge
capabilities for safe updates.

## Configuration

### Update Schedule

- **Python dependencies**: Daily at 06:00 UTC
- **GitHub Actions**: Weekly at 06:00 UTC  
- **Node.js dependencies**: Daily at 06:00 UTC (when applicable)

### Grouping Strategy

#### Python Dependencies

- **python-runtime**: Core application dependencies (Flask, Pydantic, SQLAlchemy, etc.)
- **python-tooling**: Development and testing tools (pytest, bandit, etc.)

#### GitHub Actions

- **ghactions-minor-patch**: All GitHub Actions grouped together

#### Node.js Dependencies

- **npm-runtime**: Core Node.js dependencies (Express, React, TypeScript, etc.)
- **npm-tooling**: Development tools (ESLint, Jest, Webpack, etc.)

### Auto-Merge Rules

Dependabot PRs are automatically merged when **ALL** conditions are met:

1. **Grouped update**: PR is part of a defined dependency group
2. **Safe update**: Patch or minor version updates only (no major versions)
3. **CI passes**: All required status checks pass
   - Security scanning (Semgrep)
   - Python CI tests
   - Other configured checks

### Manual Review Required

PRs require manual review in these cases:

- Major version updates
- Individual (non-grouped) dependency updates
- Security vulnerabilities requiring immediate attention
- CI checks fail

## Ignored Updates

Major version updates are ignored for critical dependencies to prevent breaking changes:

- Flask
- Pydantic  
- SQLAlchemy

These can be updated manually when ready for testing.

## Security Updates

Security updates are always allowed, even for major versions, and will bypass normal ignore rules.

## Branch Protection

The main branch is protected with these requirements:

- At least 1 PR review required
- Branches must be up to date before merging
- Required status checks:
  - Semgrep security scanning
  - Python CI tests
- Only squash merges allowed

## Monitoring

- Maximum 5 open Python PRs
- Maximum 2 open GitHub Actions PRs  
- Maximum 3 open Node.js PRs
- Automatic rebase strategy enabled

## Troubleshooting

### Auto-merge not working

1. Check if PR is part of a defined group
2. Verify it's a patch/minor update
3. Ensure all CI checks are passing
4. Check branch protection rules are met

### Too many open PRs

Dependabot will automatically limit the number of open PRs per ecosystem. Merge or close existing PRs to allow
new ones.

### Major version updates needed

Major version updates require manual review:

1. Create a separate branch for testing
2. Update dependencies manually
3. Run full test suite
4. Create PR for review

## Related Files

- `.github/dependabot.yml` - Main configuration
- `.github/workflows/dependabot-auto-merge.yml` - Auto-merge workflow
- Branch protection rules in GitHub repository settings
