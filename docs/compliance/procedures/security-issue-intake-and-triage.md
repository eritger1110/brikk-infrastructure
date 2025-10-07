# Security Issue Intake and Triage

## 1. Introduction

This document outlines the procedure for intaking, triaging, and managing security issues at Brikk. The goal is to ensure that all reported security concerns are promptly and appropriately addressed, minimizing risk to the organization and its customers.

## 2. Reporting Security Issues

Security issues can be reported through two primary channels:

*   **Internal Reporting**: Employees and contractors must report any suspected security issue immediately to the Security Team via the internal ticketing system or a designated security email alias.
*   **External Reporting**: External parties, such as security researchers, should report vulnerabilities as described in our root `SECURITY.md` file. This ensures reports are routed directly to the appropriate team.

## 3. Triage Process

All reported security issues are managed by the Incident Response Team (IRT), which performs the initial triage.

### 3.1. Initial Assessment

Upon receipt of a security issue report, the IRT will perform an initial assessment to:

1.  **Validate the Issue**: Confirm that the report describes a legitimate security concern.
2.  **Assess the Impact**: Determine the potential business and customer impact.
3.  **Determine the Scope**: Identify the systems, data, and services that are affected.

### 3.2. Prioritization

Based on the initial assessment, the issue is assigned a severity level. This prioritization determines the urgency and allocation of resources for remediation. We use the following severity levels:

| Severity | Description | Response Time SLA |
| :--- | :--- | :--- |
| **Critical** | A vulnerability that could lead to immediate, widespread compromise of sensitive data or system availability. | Acknowledgment: < 1 hour<br>Remediation: < 24 hours |
| **High** | A vulnerability that could lead to the compromise of sensitive data or disrupt key business functions, but with mitigating factors. | Acknowledgment: < 4 hours<br>Remediation: < 7 days |
| **Medium** | A vulnerability that could expose non-sensitive information or affect a limited number of users. | Acknowledgment: < 24 hours<br>Remediation: < 30 days |
| **Low** | A minor security issue with low impact that does not pose an immediate threat. | Acknowledgment: < 72 hours<br>Remediation: < 90 days |

## 4. Communication and Escalation

Throughout the lifecycle of a security issue, the IRT is responsible for communicating with relevant stakeholders, including the reporting party, internal engineering teams, and management.

For **High** and **Critical** severity issues, the IRT will immediately escalate to senior management and the legal team, as outlined in the [Incident Response Plan](../policies/incident-response-plan.md).

## 5. Remediation and Verification

Once an issue is triaged and prioritized, it is assigned to the appropriate engineering team for remediation. After a fix is developed, it must be:

1.  **Tested**: The fix is deployed to a non-production environment for validation.
2.  **Verified**: The Security Team confirms that the vulnerability is no longer present.
3.  **Deployed**: The fix is deployed to production following the [Production Deployment Checklist](./production-deployment-checklist.md).

All actions taken are documented in the [Incident Log](../evidence-templates/incident-log.csv).

## 6. References

*   [SECURITY.md](../../../SECURITY.md)
*   [Incident Response Plan](../policies/incident-response-plan.md)

## 7. Revision History

| Version | Date | Author | Changes |
| :--- | :--- | :--- | :--- |
| 1.0 | 2025-10-07 | Manus AI | Initial draft. |

