# Brikk API Endpoints

This document describes the API endpoints available in the Brikk infrastructure platform.

## Authentication

The Brikk API uses HMAC-SHA256 signature-based authentication with the following headers:

- `X-Brikk-Key`: API key ID
- `X-Brikk-Timestamp`: Unix timestamp (seconds)
- `X-Brikk-Signature`: HMAC-SHA256 signature of `{timestamp}.{body}`

Alternative: Some endpoints support `Authorization: Bearer {api_key}` for simpler authentication.

## Endpoints

| Method | Path | Description | Auth | Request | Response |
|---:|:---|:---|:---|:---|:---|
| GET | `/healthz` | Health check endpoint | None | - | `200 OK` `{status: "ok"}` |
| GET | `/readyz` | Readiness check | None | - | `200 OK` `{status: "ready"}` |
| GET | `/api/v1/coordination/health` | Coordination service health | None | - | `200 OK` Health status |
| GET | `/auth/_ping` | Auth service ping | None | - | `200 OK` Pong response |
| POST | `/auth/login` | User login | None | `{email, password}` | `200 OK` JWT token |
| POST | `/auth/complete-signup` | Complete signup | None | User data | `200 OK` Success |
| GET | `/auth/me` | Get current user | JWT | - | `200 OK` User profile |
| POST | `/auth/logout` | Logout | JWT | - | `200 OK` Success |
| GET | `/api/v1/agents` | List all agents | API Key | `?org_id=...` | `200 OK` List of agents |
| POST | `/api/v1/agents` | Create new agent | API Key | Agent data | `201 Created` Created agent |
| POST | `/api/v1/coordination` | Send coordination message | HMAC | Message envelope | `202 Accepted` Delivery receipt |
| GET | `/api/v1/economy/balance` | Get organization balance | API Key | `?org_id=...` | `200 OK` `{balance: int}` |
| POST | `/api/v1/economy/transaction` | Create transaction | API Key | Transaction data | `201 Created` Transaction record |
| GET | `/api/v1/reputation/summary` | Get reputation summary | API Key | `?org_id=...` | `200 OK` Reputation summary |
| GET | `/api/v1/reputation/agents` | List agent reputations | API Key | `?org_id=...` | `200 OK` Agent reputation list |
| POST | `/api/billing/portal` | Create Stripe billing portal session | JWT | `{customer_id?}` | `200 OK` `{url: string}` |

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
