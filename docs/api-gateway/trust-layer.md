# Brikk API Gateway: Trust Layer (Phase 7)

**Version:** 1.0
**Status:** Implemented

This document outlines the architecture and functionality of the **Network Intelligence & Federated Trust Layer**, a comprehensive reputation and risk management system for the Brikk API Gateway.

## 1. Overview

The Trust Layer provides a robust framework for assessing the trustworthiness of organizations and agents within the Brikk ecosystem. It enables:

- **Reputation Scoring:** Quantifiable 0-100 scores for all network participants.
- **Risk Assessment:** Real-time risk analysis for every API request.
- **Adaptive Security:** Dynamic rate limiting based on risk level.
- **Web-of-Trust:** A decentralized attestation system where orgs vouch for each other.
- **Trusted Discovery:** Reputation-based ranking for agent discovery.

## 2. Core Components

### 2.1. Reputation Engine

The Reputation Engine computes a 0-100 score for every organization and agent based on a weighted average of multiple factors over a 30-day window.

| Factor | Weight | Description |
|---|---|---|
| **Commerce Score** | 40% | Based on transaction volume, value, and success rate. Rewards high-value, reliable commerce. |
| **Hygiene Score** | 30% | Based on API uptime, error rates, and security best practices. Rewards well-behaved APIs. |
| **Attestation Score** | 20% | Based on weighted attestations from other trusted organizations. Rewards community trust. |
| **Longevity Score** | 10% | Based on the age of the organization or agent. Rewards long-term participation. |

**Batch Job:**
- Runs every 24 hours to recompute and cache reputation scores in `reputation_snapshots`.
- Ensures scores are kept up-to-date without real-time performance overhead.

### 2.2. Risk Middleware

The Risk Middleware assesses the risk of every incoming API request in real-time.

**Risk Scoring Model:**
| Factor | Weight | Description |
|---|---|---|
| **Reputation** | 60% | Cached reputation score of the actor (org or agent). |
| **Recent Risk Events** | 25% | High/medium/low severity events in the last 7 days (e.g., failed auth, high error rates). |
| **Auth Anomalies** | 15% | Suspicious authentication patterns (e.g., rapid IP changes, failed token validation). |

**Adaptive Rate Limits:**
| Risk Level | Score Range | Rate Limit Multiplier | Effect |
|---|---|---|---|
| **Low** | >= 70 | 1.2x | +20% burst allowance for trusted actors. |
| **Medium** | 40-69 | 1.0x | Plan baseline. |
| **High** | < 40 | 0.5x | 50% of baseline for risky actors. |

### 2.3. Attestations (Web-of-Trust)

Organizations can vouch for the trustworthiness of other orgs or agents through attestations.

- **Weight:** 0.0-1.0 (strength of endorsement)
- **Statement:** Free-text explanation
- **Evidence URL:** Optional supporting documentation
- **Time Decay:** Attestations gradually lose influence over 90 days.

### 2.4. Discovery Ranking

The agent registry now supports sorting by reputation, allowing users to find the most trusted agents first.

- **`sort=reputation`** (default): Highest reputation score first.
- **`sort=recency`**: Newest agents first.
- **`sort=name`**: Alphabetical order.

## 3. API Endpoints

### Reputation
- `GET /v1/trust/reputation/{subject_type}/{subject_id}`: Get bucketed reputation score.
- `POST /v1/trust/reputation/recompute`: (Admin) Trigger batch recomputation.

### Attestations
- `POST /v1/trust/attestations`: Create a new attestation.
- `GET /v1/trust/attestations`: List attestations for a subject.
- `GET /v1/trust/attestations/{id}`: Get a specific attestation.
- `DELETE /v1/trust/attestations/{id}`: Revoke an attestation.

### Explainers
- `GET /v1/trust/explainers/reputation/{subject_type}/{subject_id}`: Get a detailed breakdown of a reputation score (owner only).

## 4. Privacy

- **Score Bucketing:** Public reputation scores are bucketed (e.g., "80-100") to protect raw scores.
- **Explainers:** Detailed score explanations are only available to the subject owner.
- **Anonymity:** Risk events are aggregated and do not expose sensitive user data.

## 5. Future Work

- **Step-Up Verification:** Integrate MFA/OTP for high-risk write operations.
- **Dispute Resolution:** Allow organizations to dispute negative reputation events.
- **Global Trust Network:** Federate trust scores across multiple Brikk instances.

