# Controls Matrix

## 1. Introduction

This document maps Brikk's implemented security controls to the relevant requirements of the HIPAA Security Rule and the SOC 2 Trust Services Criteria. This matrix is a living document that will be updated as new controls are implemented.

## 2. Controls Mapping

| Control | HIPAA Security Rule | SOC 2 Trust Services Criteria | Implementation |
| :--- | :--- | :--- | :--- |
| **Rate Limiting** | 164.312(a)(2)(iv) - Person or entity authentication<br>164.312(b) - Audit controls | CC6.1 - Logical and physical access controls<br>CC7.1 - System operations | Implemented on all public-facing API endpoints to protect against denial-of-service attacks and brute-force authentication attempts. |
| **HMAC Authentication** | 164.312(a)(2)(iv) - Person or entity authentication<br>164.312(c)(1) - Integrity | CC6.1 - Logical and physical access controls<br>CC8.1 - Change management | All API requests are authenticated using HMAC signatures to ensure the integrity and authenticity of the data. |
| **Idempotency** | 164.312(c)(1) - Integrity | CC7.1 - System operations | All state-changing API requests are idempotent to prevent duplicate transactions and ensure data integrity. |
| **Observability** | 164.312(b) - Audit controls | CC7.2 - Monitoring of controls | Comprehensive logging and monitoring of all systems and applications to detect and respond to security incidents in a timely manner. |
| **CI/CD Security Scans** | 164.308(a)(1)(ii)(A) - Risk analysis<br>164.308(a)(1)(ii)(B) - Risk management | CC7.1 - System operations<br>CC8.1 - Change management | Automated security scanning in the CI/CD pipeline (SAST, SCA, secret detection) to identify and remediate vulnerabilities before they are deployed to production. |

## 3. Revision History

| Version | Date | Author | Changes |
| :--- | :--- | :--- | :--- |
| 1.0 | 2025-10-07 | Manus AI | Initial draft. |

