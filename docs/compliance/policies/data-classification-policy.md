# Data Classification Policy

## Policy Ownership and Review

| Role | Responsibility | Review Cadence |
| --- | --- | --- |
| **Owner** | Security Team | Quarterly |
| **Approver** | Chief Privacy Officer | Annual |
| **Reviewer** | Legal Team | Semi-Annual |

## 1. Introduction

This policy establishes a framework for classifying Brikk's data based on its sensitivity, value, and criticality. Proper data classification is essential for ensuring that data is protected with the appropriate level of security controls and for complying with legal and regulatory requirements.

## 2. Scope

This policy applies to all data that is created, stored, processed, or transmitted by Brikk, regardless of its format or location. This includes data on servers, laptops, mobile devices, and in the cloud.

## 3. Data Classification Levels

Brikk has established the following four data classification levels:

| Level | Description | Examples |
| --- | --- | --- |
| **Restricted** | Highly sensitive data that, if disclosed, could cause significant harm to Brikk or its customers. | - Protected Health Information (PHI)<br>- Personally Identifiable Information (PII)<br>- Financial account numbers<br>- Authentication credentials |
| **Confidential** | Sensitive data that is intended for internal use only. | - Business plans<br>- Financial reports<br>- Employee records<br>- Customer contracts |
| **Internal** | Data that is not intended for public disclosure but has a low sensitivity. | - Internal communications<br>- Meeting minutes<br>- Project documentation |
| **Public** | Data that is intended for public consumption. | - Marketing materials<br>- Press releases<br>- Publicly available website content |

## 4. Handling Requirements

Each data classification level has a set of handling requirements that specify the minimum security controls that must be applied. These requirements are summarized in the table below:

| Control | Public | Internal | Confidential | Restricted |
| --- | :---: | :---: | :---: | :---: |
| **Encryption in Transit** | | ✓ | ✓ | ✓ |
| **Encryption at Rest** | | | ✓ | ✓ |
| **Access Control** | | ✓ | ✓ | ✓ |
| **Logging and Monitoring** | | | ✓ | ✓ |
| **Data Loss Prevention (DLP)** | | | | ✓ |

## 5. Responsibilities

| Role | Responsibilities |
| --- | --- |
| **Data Owners** | - Assigning the appropriate classification level to their data.<br>- Reviewing and updating data classifications on a regular basis. |
| **Data Custodians** | - Implementing and maintaining the security controls required for each data classification level. |
| **All Employees** | - Handling all data in accordance with its classification level. |

## 6. Enforcement

Violation of this policy may result in disciplinary action, up to and including termination of employment. Unauthorized disclosure of sensitive data may also result in legal action.

## 7. References

- [NIST Special Publication 800-60](https://csrc.nist.gov/publications/detail/sp/800-60/vol-1-rev-1/final)
- [HIPAA Privacy Rule (45 CFR Part 160 and Subparts A and E of Part 164)](https://www.hhs.gov/hipaa/for-professionals/privacy/index.html)

## 8. Revision History

| Version | Date | Author | Changes |
| --- | --- | --- | --- |
| 1.0 | 2025-10-07 | Manus AI | Initial draft. |
