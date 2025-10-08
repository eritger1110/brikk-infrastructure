# Security CI Documentation

This document describes the security scanning workflows implemented in the Brikk Infrastructure CI/CD pipeline.

## 🛡️ Overview

The security CI pipeline consists of three main components:

1. **Semgrep** - Static Application Security Testing (SAST)
2. **Gitleaks** - Secret Detection and Credential Scanning
3. **OWASP Dependency Check** - Software Composition Analysis (SCA)

All security scans are designed to be **deterministic**, **reliable**, and **fail-fast** on real security issues while avoiding false positives and infrastructure-related failures.

## 🔍 Security Scans

### Semgrep (Static Analysis)

**Purpose**: Detect security vulnerabilities, code quality issues, and anti-patterns in source code.

**Configuration**:
- **Rulesets**: OWASP Top 10, secrets, Python, Flask, security-audit
- **Timeout**: 180 seconds
- **SARIF Generation**: Disabled (to avoid billing issues)
- **Execution**: Always runs on all file types

**What it catches**:
- SQL injection vulnerabilities
- Cross-site scripting (XSS) patterns
- Insecure cryptographic usage
- Authentication and authorization flaws
- Code injection vulnerabilities
- Hardcoded secrets and credentials

### Gitleaks (Secret Detection)

**Purpose**: Prevent accidental commit of secrets, API keys, passwords, and other sensitive credentials.

**Configuration**:
- **Scan Target**: Current workspace only (deterministic)
- **History**: Full checkout (`fetch-depth: 0`) for comprehensive scanning
- **Output**: JSON format with redacted secrets
- **Execution**: Always runs on all commits and PRs

**What it catches**:
- API keys (AWS, GitHub, Stripe, etc.)
- Database connection strings
- Private keys and certificates
- OAuth tokens and secrets
- Hardcoded passwords
- Cloud service credentials

**Deterministic Scanning**:
```bash
# Downloads latest Gitleaks binary
curl -sSL https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_$(uname -s)_$(uname -m).tar.gz -o gl.tgz
tar -xzf gl.tgz gitleaks

# Scans current workspace only (not git history)
./gitleaks detect --no-banner --redact --report-format json --report-path gitleaks.json --source .
```

### OWASP Dependency Check (SCA)

**Purpose**: Identify known vulnerabilities in third-party dependencies and libraries.

**Configuration**:
- **Trigger**: Only when dependency manifests exist
- **CVSS Threshold**: 7.0 (High and Critical vulnerabilities)
- **Formats**: JSON and HTML reports
- **Suppression**: Uses `suppression.xml` for false positive management

**Supported Manifests**:
- `package-lock.json` (Node.js)
- `yarn.lock` (Node.js/Yarn)
- `pnpm-lock.yaml` (Node.js/pnpm)
- `requirements.txt` (Python/pip)
- `poetry.lock` (Python/Poetry)
- `Pipfile.lock` (Python/Pipenv)
- `Gemfile.lock` (Ruby)
- `composer.lock` (PHP)

**Guard Condition**:
```yaml
if: ${{ hashFiles('**/package-lock.json', '**/yarn.lock', '**/pnpm-lock.yaml', '**/requirements.txt', '**/poetry.lock', '**/Pipfile.lock', '**/Gemfile.lock', '**/composer.lock') != '' }}
```

## 🚫 What's NOT Included

### SARIF Uploads Disabled

SARIF (Static Analysis Results Interchange Format) uploads to GitHub Security tab are **intentionally disabled** to avoid:

- GitHub billing limitations
- Account lockout issues
- CI pipeline failures due to permissions
- Dependency on GitHub Advanced Security features

**Re-enabling SARIF**: When GitHub billing/permissions are resolved, SARIF uploads can be re-enabled by:

1. Adding `generateSarif: true` to Semgrep configuration
2. Adding SARIF upload steps with `github/codeql-action/upload-sarif@v3`
3. Setting `security-events: write` permissions

### Artifact Uploads Minimized

- **Dependency Check**: Reports stored as artifacts (30-day retention)
- **Gitleaks**: No artifacts uploaded (JSON report generated locally)
- **Semgrep**: No artifacts uploaded (console output only)

## 🔧 Local Development

### Running Gitleaks Locally

```bash
# Download Gitleaks binary
curl -sSL https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_$(uname -s)_$(uname -m).tar.gz -o gl.tgz
tar -xzf gl.tgz gitleaks

# Scan current directory
./gitleaks detect --no-banner --redact --source .

# Scan with verbose output
./gitleaks detect --no-banner --redact --source . --verbose

# Generate report
./gitleaks detect --no-banner --redact --source . --report-format json --report-path gitleaks.json
```

### Running OWASP Dependency Check Locally

```bash
# Install OWASP Dependency Check CLI
# See: https://owasp.org/www-project-dependency-check/

# Run dependency check
dependency-check --project "brikk-infrastructure" --scan . --format JSON --format HTML --failOnCVSS 7
```

### Running Semgrep Locally

```bash
# Install Semgrep
pip install semgrep

# Run with same rulesets as CI
semgrep --config=p/owasp-top-ten --config=p/secrets --config=p/python --config=p/flask --config=p/security-audit .

# Run specific ruleset
semgrep --config=p/owasp-top-ten .

# Generate JSON output
semgrep --config=p/owasp-top-ten --json --output=semgrep-results.json .
```

## 📊 CI Behavior

### Success Conditions

- **Semgrep**: No HIGH or CRITICAL findings
- **Gitleaks**: No secrets detected in workspace
- **OWASP DC**: No vulnerabilities with CVSS ≥ 7.0

### Failure Conditions

- **Semgrep**: HIGH or CRITICAL security vulnerabilities found
- **Gitleaks**: Secrets or credentials detected
- **OWASP DC**: Dependencies with CVSS ≥ 7.0 vulnerabilities

### Skipping Conditions

- **OWASP DC**: Skips when no dependency manifests found
- **All scans**: Continue on infrastructure failures (network, billing, etc.)

## 🔒 Security Posture

### Threat Coverage

| Threat Category | Tool | Coverage |
|----------------|------|----------|
| Code Vulnerabilities | Semgrep | SQL injection, XSS, crypto issues |
| Secret Exposure | Gitleaks | API keys, passwords, certificates |
| Dependency Vulnerabilities | OWASP DC | Known CVEs in third-party libs |
| Configuration Issues | Semgrep | Insecure defaults, misconfigurations |
| Authentication Flaws | Semgrep | Auth bypass, weak authentication |

### Compliance Alignment

- **OWASP Top 10**: Covered by Semgrep rulesets
- **CWE (Common Weakness Enumeration)**: Mapped through OWASP DC
- **CVE (Common Vulnerabilities and Exposures)**: Tracked by OWASP DC
- **NIST Cybersecurity Framework**: Supports Identify and Protect functions

## 🛠️ Maintenance

### Suppression Management

False positives can be suppressed using `suppression.xml`:

```xml
<suppress>
    <notes><![CDATA[
    Justification for suppression
    Review date: YYYY-MM-DD
    ]]></notes>
    <packageUrl regex="true">^pkg:pypi/package-name@.*$</packageUrl>
    <cve>CVE-YYYY-NNNNN</cve>
</suppress>
```

### Regular Reviews

- **Monthly**: Review suppression file for outdated entries
- **Quarterly**: Update Semgrep rulesets and Gitleaks patterns
- **Annually**: Review CVSS thresholds and security requirements

### Tool Updates

- **Gitleaks**: Auto-downloads latest release in CI
- **Semgrep**: Uses official action (auto-updated)
- **OWASP DC**: Uses official action (auto-updated)

## 🚨 Incident Response

### When Scans Fail

1. **Immediate**: Block merge/deployment until resolved
2. **Investigate**: Determine if finding is true positive or false positive
3. **Remediate**: Fix vulnerability or add justified suppression
4. **Validate**: Re-run scans to confirm resolution

### Emergency Bypasses

In critical situations, security scans can be temporarily bypassed:

```yaml
# Add to workflow file temporarily
if: false  # Emergency bypass - remove after fix
```

**⚠️ Warning**: Emergency bypasses must be:
- Documented with justification
- Approved by security team
- Removed as soon as possible
- Tracked in incident reports

## 📈 Metrics and Monitoring

### Key Metrics

- **Scan Success Rate**: Percentage of successful scans
- **Mean Time to Resolution**: Average time to fix findings
- **False Positive Rate**: Percentage of findings that are false positives
- **Coverage**: Percentage of codebase scanned

### Monitoring

- **CI Dashboard**: Track scan results and trends
- **Alerting**: Notify on scan failures or new vulnerabilities
- **Reporting**: Weekly security posture reports

## 🔄 Future Enhancements

### Planned Improvements

1. **SARIF Integration**: Re-enable when billing resolved
2. **Custom Rules**: Add Brikk-specific security patterns
3. **Vulnerability Database**: Integrate with threat intelligence
4. **Automated Remediation**: Auto-fix certain vulnerability types

### Integration Opportunities

- **IDE Integration**: Real-time security feedback during development
- **Pre-commit Hooks**: Catch issues before commit
- **Security Dashboard**: Centralized security metrics and trends
- **Compliance Reporting**: Automated compliance evidence generation

## 📚 References

- [Semgrep Documentation](https://semgrep.dev/docs/)
- [Gitleaks Documentation](https://github.com/gitleaks/gitleaks)
- [OWASP Dependency Check](https://owasp.org/www-project-dependency-check/)
- [SARIF Specification](https://sarifweb.azurewebsites.net/)
- [GitHub Security Features](https://docs.github.com/en/code-security)

## 📝 Recent Changes

- **December 2024**: Stripe upgraded to `~=13.0.1`, validated in staging, and merged to main.

## CI Truth Table

This table documents the automated checks enforced by our CI pipeline on every pull request.

| Check | Where Enforced | Fails PR? | Evidence Location |
|---|---|---|---|
| **Python 3.11 Setup** | `.github/workflows/ci.yaml` | ✅ Yes | CI run logs |
| **Dependency Cache** | `.github/workflows/ci.yaml` | ❌ No | CI run logs |
| **`pytest` Smoke Tests** | `.github/workflows/ci.yaml` | ✅ Yes | CI run logs, test artifacts |
| **`flake8` Syntax Lint** | `.github/workflows/ci.yaml` | ❌ No | CI run logs (informational) |
| **`black --check`** | `.github/workflows/ci.yaml` | ❌ No | CI run logs (informational) |
| **`markdownlint`** | `.github/workflows/docs-lint.yml` | ✅ Yes | CI run logs |
| **Semgrep (SAST)** | `.github/workflows/ci-security.yml` | ✅ Yes | CI run logs |
| **Gitleaks (Secrets)** | `.github/workflows/ci-security.yml` | ✅ Yes | CI run logs |
| **OWASP Dependency Check** | `.github/workflows/ci-security.yml` | ✅ Yes | CI run logs, test artifacts |

---

**Last Updated**: December 2024  
**Review Schedule**: Quarterly  
**Owner**: Brikk Security Team
