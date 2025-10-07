# Security at Brikk

## Our Commitment

At Brikk, we are committed to the security of our systems and the protection of our customers' data. We follow industry best practices and have implemented a comprehensive security program to ensure that our platform is secure and compliant with relevant regulations.

## Reporting a Vulnerability

We value the contributions of security researchers and welcome responsible disclosure of any security vulnerabilities you may find. If you believe you have discovered a security issue, please report it to us by emailing [security@getbrikk.com](mailto:security@getbrikk.com).

We will make every effort to respond to your report in a timely manner and will work with you to ensure that the issue is resolved as quickly as possible. For more details on our triage and remediation process, please see our [Security Issue Intake and Triage procedure](./docs/compliance/procedures/security-issue-intake-and-triage.md).

## Security Features

We have implemented a number of security features to protect our systems and data, including:

-   **Rate Limiting**: To protect against denial-of-service attacks and brute-force authentication attempts.
-   **HMAC Authentication**: To ensure the integrity and authenticity of all API requests.
-   **Idempotency**: To prevent duplicate transactions and ensure data integrity.
-   **Observability**: Comprehensive logging and monitoring to detect and respond to security incidents.
-   **CI/CD Security Scans**: Automated security scanning in our CI/CD pipeline to identify and remediate vulnerabilities before they are deployed to production.

For a more detailed mapping of our security controls to industry standards, please see our [Controls Matrix](./docs/compliance/controls-matrix.md).

