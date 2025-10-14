# Brikk API Endpoints

This document describes the API endpoints available in the Brikk infrastructure platform.

## Authentication

The Brikk API uses HMAC-SHA256 signature-based authentication with the following headers:

- `X-Brikk-Key`: API key ID
- `X-Brikk-Timestamp`: Unix timestamp (seconds)
- `X-Brikk-Signature`: HMAC-SHA256 signature of `{timestamp}.{body}`

Alternative: Some endpoints support `Authorization: Bearer {api_key}` for simpler authentication.

## Endpoints

| Method | Path | Params | Returns | Auth | Notes |
|--------|------|--------|---------|------|-------|
| **Health & Status** |
| GET | `/healthz` | - | `{status: "ok"}` | None | Health check endpoint |
| GET | `/readyz` | - | `{status: "ready"}` | None | Readiness check |
| GET | `/api/v1/coordination/health` | - | Health status | None | Coordination service health |
| **Authentication** |
| GET | `/auth/_ping` | - | Pong response | None | Auth service ping |
| POST | `/auth/login` | `{email, password}` | JWT token | None | User login |
| POST | `/auth/complete-signup` | User data | Success | None | Complete signup |
| GET | `/auth/me` | - | User profile | JWT | Get current user |
| POST | `/auth/logout` | - | Success | JWT | Logout |
| **Agents** |
| GET | `/agents` | `?org_id=...` | List of agents | API Key | List all agents |
| POST | `/agents` | Agent data | Created agent | API Key | Create new agent |
| **Coordination** |
| POST | `/api/v1/coordination` | Message envelope | Delivery receipt | HMAC | Send coordination message |
| **Economy** |
| GET | `/api/v1/economy/balance` | `?org_id=...` | `{balance: int}` | API Key | Get organization balance |
| POST | `/api/v1/economy/transaction` | Transaction data | Transaction record | API Key | Create transaction |
| **Reputation** |
| GET | `/api/v1/reputation/summary` | `?org_id=...` | Reputation summary | API Key | Get reputation summary |
| GET | `/api/v1/reputation/agents` | `?org_id=...` | Agent reputation list | API Key | List agent reputations |
| **Billing** |
| POST | `/api/billing/portal` | `{customer_id?}` | `{url: string}` | JWT | Create Stripe billing portal session |

## Message Envelope Format (Coordination)

```json
{
  "version": "1.0",
  "message_id": "uuid-v4",
  "ts": "ISO-8601 timestamp",
  "type": "event",
  "sender": {"agent_id": "string"},
  "recipient": {"agent_id": "string"},
  "payload": {},
  "ttl_ms": 60000
}
```

## Error Responses

All endpoints return standard error responses:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {}
}
```

Common HTTP status codes:
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error
- `502` - Bad Gateway (external service error)
