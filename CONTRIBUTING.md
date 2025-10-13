# Contributing to Brikk Infrastructure

Thank you for your interest in contributing to Brikk Infrastructure! This document outlines our development process, CI requirements, and guidelines for maintaining our security and quality standards.

## Development Workflow

### Getting Started

1. Fork the repository and create a feature branch from `main`
2. Use descriptive branch names: `feature/<area>-<description>` or `fix/<issue-description>`
3. Make your changes following our coding standards
4. Ensure all CI checks pass before requesting review
5. Submit a pull request with a clear description

### Branch Naming Convention

- **Features**: `feature/coordination-api-v2`
- **Bug Fixes**: `fix/hmac-validation-timing`
- **Security**: `security/dependency-updates`
- **Documentation**: `docs/api-documentation`
- **CI/Infrastructure**: `ci/security-baseline`

## CI Requirements

All pull requests must pass our comprehensive CI pipeline before merging. Our CI system includes multiple security and quality gates designed to maintain the highest standards for production deployment.

### Required CI Checks

#### Python Testing (`ci-python.yml`)
- **Unit Tests**: All tests must pass with pytest
- **Code Coverage**: Maintain minimum coverage thresholds
- **Security Scanning**: Bandit static analysis for security vulnerabilities
- **Dependency Audit**: pip-audit for known vulnerabilities in dependencies
- **Supported Versions**: Python 3.11 and 3.12

#### Node.js Testing (`ci-node.yml`)
- **Linting**: ESLint for code quality and consistency
- **Unit Tests**: Jest test suite execution
- **Dependency Audit**: npm audit for high-severity vulnerabilities
- **Supported Versions**: Node.js 18.x and 20.x

#### Security Scanning (`ci-security.yml`)
- **Static Analysis**: Semgrep with OWASP and security rulesets
- **Secret Detection**: Automated scanning for hardcoded credentials
- **Dependency Check**: OWASP dependency vulnerability analysis
- **Failure Threshold**: High and critical findings will fail the build

#### Container Security (`ci-trivy.yml`)
- **Repository Scan**: Filesystem vulnerability scanning
- **Docker Image Scan**: Container image security analysis
- **Configuration Scan**: Infrastructure as Code security review
- **Compliance**: Fails on high and critical vulnerabilities

#### Supply Chain Security (`ci-sbom.yml`)
- **SBOM Generation**: CycloneDX Software Bill of Materials
- **Dependency Tracking**: Complete inventory of all components
- **Artifact Storage**: SBOMs stored for compliance and auditing

### Security Requirements

#### Secret Management
- Never commit secrets, API keys, or credentials to the repository
- Use environment variables for all sensitive configuration
- The secret scanning workflow will automatically detect and block common secret patterns
- Test your changes locally to ensure no secrets are inadvertently included

#### Dependency Management
- Keep dependencies updated through Dependabot automation
- Review and approve dependency updates promptly
- Address high and critical vulnerability findings immediately
- Use pinned versions for production dependencies

#### Code Security
- Follow secure coding practices outlined in our Semgrep rules
- Validate all user inputs and sanitize outputs
- Use parameterized queries to prevent SQL injection
- Implement proper authentication and authorization checks

## Code Quality Standards

### Python Code Standards
- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Write comprehensive docstrings for public APIs
- Maintain test coverage above 80%
- Use meaningful variable and function names

### Security Practices
- Implement defense-in-depth security measures
- Use constant-time comparisons for sensitive operations
- Validate and sanitize all external inputs
- Log security events appropriately (without exposing sensitive data)
- Follow the principle of least privilege

### Testing Requirements
- Write unit tests for all new functionality
- Include both positive and negative test cases
- Test error handling and edge cases
- Mock external dependencies appropriately
- Ensure tests are deterministic and reliable

## Pull Request Process

### Before Submitting
1. Run the full test suite locally: `pytest tests/`
2. Check for security issues: `bandit -r src/`
3. Verify no secrets are committed: Review your changes carefully
4. Update documentation if needed
5. Ensure your branch is up to date with `main`

### PR Description Template
```markdown
## Description
Brief description of changes and motivation

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Security update
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Security scans pass
- [ ] Manual testing completed

## Security Considerations
- [ ] No secrets or credentials committed
- [ ] Input validation implemented
- [ ] Authorization checks in place
- [ ] Security implications reviewed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] CI checks pass
```

### Review Process
- All PRs require at least one approval from a maintainer
- Security-related changes require additional security team review
- CI must pass completely before merge approval
- Breaking changes require special consideration and documentation

## Feature Flags and Safe Deployment

### Feature Flag Requirements
- All new features must be behind feature flags
- Default to safe values (typically disabled)
- Use environment variables for flag configuration
- Document flag behavior and rollout plan

### Example Feature Flag Implementation
```python
ENABLE_NEW_FEATURE = os.getenv("BRIKK_NEW_FEATURE_ENABLED", "0") == "1"

if ENABLE_NEW_FEATURE:
    # New feature implementation
    pass
else:
    # Existing behavior
    pass
```

## Local Development Setup

### Prerequisites
- Python 3.11 or 3.12
- Node.js 18.x or 20.x (if working with frontend components)
- Docker (for container testing)
- Git

### Environment Setup
```bash
# Clone the repository
git clone https://github.com/eritger1110/brikk-infrastructure.git
cd brikk-infrastructure

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install pytest bandit pip-audit  # Development tools

# Run tests
pytest tests/

# Run security scans
bandit -r src/
pip-audit
```

## Getting Help

### Resources
- **Documentation**: Check existing docs and README files
- **Issues**: Search existing GitHub issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Security**: Email security@getbrikk.com for security-related concerns

### Contact
- **General Questions**: Create a GitHub issue
- **Security Issues**: security@getbrikk.com
- **Maintainers**: @eritger1110

## License

By contributing to Brikk Infrastructure, you agree that your contributions will be licensed under the same license as the project.

---

*This contributing guide is updated regularly to reflect our evolving development practices and security requirements.*

_


### Pre-commit
Install once:
```bash
pip install pre-commit
pre-commit install
```

