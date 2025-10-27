# Brikk Phase 10-12 Implementation Plan

## Status: In Progress

### ✅ Completed Phases (1-3)

#### Phase 1: Database Setup
- [x] Created `UsageEvent` model for cost tracking
- [x] Added `soft_cap_usd` and `hard_cap_usd` to `ApiKey` model
- [x] Created 3 migration files (001, 002, 003)
- [x] Integrated with existing Flask-SQLAlchemy setup

**Files Created:**
- `src/models/usage_event.py`
- `migrations/versions/001_initial_schema.sql`
- `migrations/versions/002_add_budget_fields.sql`
- `migrations/versions/003_create_usage_events.sql`

#### Phase 2: Authentication & Authorization
- [x] API key authentication middleware (`X-Brikk-API-Key` header)
- [x] Per-key rate limiting (in-memory, configurable via env)
- [x] Budget enforcement (soft cap warning, hard cap block)
- [x] Rate limit headers (`X-RateLimit-*`)
- [x] Budget headers (`X-Brikk-Usage-Today`, `X-Brikk-Soft-Cap-Exceeded`)

**Files Created:**
- `src/middleware/auth_middleware.py`
- `src/middleware/__init__.py`

**Environment Variables:**
- `BRIKK_REQUIRE_AUTH` - Enable/disable auth (default: false)
- `BRIKK_DEFAULT_SOFT_CAP_USD` - Default soft cap (default: 5.00)
- `BRIKK_DEFAULT_HARD_CAP_USD` - Default hard cap (default: 10.00)
- `BRIKK_RATE_LIMIT_PER_MIN` - Default rate limit (default: 60)

#### Phase 3: Usage Metering & Cost Calculation
- [x] Cost calculation service with provider/model pricing
- [x] Usage metering service for recording events
- [x] Server-side cost calculation (no client trust)
- [x] Database persistence for all usage events

**Files Created:**
- `src/services/cost_service.py`
- `src/services/usage_metering_service.py`

**Pricing Implemented:**
- OpenAI: gpt-4o-mini, gpt-4o, gpt-3.5-turbo
- Mistral: mistral-small-latest, mistral-medium-latest, mistral-large-latest

---

### 🔄 Remaining Phases (4-13)

#### Phase 4: Resilience
**Goal:** Prevent cascading failures, handle provider outages gracefully

**Tasks:**
- [ ] Implement circuit breaker pattern for each provider
- [ ] Add timeout configuration (30s default)
- [ ] Add retry logic with exponential backoff (3 retries)
- [ ] Improve fallback logic in router service
- [ ] Add health checks for each provider

**Files to Create/Modify:**
- `src/services/circuit_breaker.py` ✅ (created)
- `src/services/openai_service.py` (add timeout + retry)
- `src/services/mistral_service.py` (add timeout + retry)
- `src/services/router_service.py` (improve fallback)

**Environment Variables:**
- `PROVIDER_TIMEOUT_SECONDS` - Timeout for provider calls (default: 30)
- `PROVIDER_MAX_RETRIES` - Max retries (default: 3)

---

#### Phase 5: Security
**Goal:** Harden security posture for production

**Tasks:**
- [ ] Add security headers (HSTS, X-Frame-Options, X-Content-Type-Options)
- [ ] Implement CORS allowlist (no wildcards in prod)
- [ ] Add audit logging for all authenticated requests
- [ ] Implement request signing (optional, for high-security use cases)
- [ ] Add IP whitelisting support (optional)

**Files to Create/Modify:**
- `src/middleware/security_middleware.py`
- `src/services/audit_service.py`
- `src/factory.py` (add security headers)

**Environment Variables:**
- `CORS_ALLOWED_ORIGINS` - Comma-separated list of allowed origins
- `ENABLE_AUDIT_LOGGING` - Enable audit logs (default: true)

---

#### Phase 6: Observability
**Goal:** Production-grade monitoring and debugging

**Tasks:**
- [ ] Enhance Prometheus metrics (add histograms, gauges)
- [ ] Add Sentry integration for error tracking
- [ ] Add OpenTelemetry tracing (optional)
- [ ] Create Grafana dashboard JSON
- [ ] Add structured logging with correlation IDs

**Files to Create/Modify:**
- `src/services/provider_metrics.py` (enhance existing)
- `src/services/sentry_service.py`
- `grafana/brikk-dashboard.json`
- `src/middleware/logging_middleware.py`

**Environment Variables:**
- `SENTRY_DSN` - Sentry project DSN
- `ENABLE_TRACING` - Enable OpenTelemetry (default: false)

---

#### Phase 7: OpenAPI Spec & Documentation
**Goal:** Auto-generated, interactive API documentation

**Tasks:**
- [ ] Create OpenAPI 3.0 specification
- [ ] Add Swagger UI at `/docs`
- [ ] Generate SDK stubs (Python, JavaScript, cURL)
- [ ] Add request/response examples
- [ ] Document authentication flow

**Files to Create:**
- `openapi.yaml`
- `src/routes/docs.py`
- `src/static/swagger-ui.html`

**Endpoints:**
- `GET /docs` - Swagger UI
- `GET /openapi.json` - OpenAPI spec

---

#### Phase 8: New Endpoints
**Goal:** User-facing usage and key management endpoints

**Tasks:**
- [ ] `GET /usage/me` - Get usage summary for current API key
- [ ] `POST /keys/rotate` - Rotate API key
- [ ] `GET /keys/me` - Get current API key info
- [ ] `GET /health/circuit-breakers` - Circuit breaker status

**Files to Create:**
- `src/routes/usage.py`
- `src/routes/keys.py`

**Response Examples:**
```json
// GET /usage/me
{
  "api_key_id": 123,
  "today": {
    "cost_usd": 0.45,
    "requests": 150,
    "tokens": 45000
  },
  "this_week": {...},
  "this_month": {...},
  "soft_cap_usd": 5.00,
  "hard_cap_usd": 10.00,
  "soft_cap_exceeded": false
}

// POST /keys/rotate
{
  "old_key_prefix": "bk_abc123",
  "new_key": "brikk_xyz789...",
  "rotated_at": "2025-10-26T22:00:00Z"
}
```

---

#### Phase 9: Frontend Updates
**Goal:** Update playground and create key management UI

**Tasks:**
- [ ] Add API key input to multi-provider playground
- [ ] Create `/sandbox/keys` page for key management
- [ ] Add usage dashboard widget
- [ ] Update all playgrounds to use auth
- [ ] Add "Get API Key" CTA

**Files to Create/Modify:**
- `src/static/multi-provider.html` (add API key input)
- `src/static/keys.html` (new page)
- `src/static/bridge.html` (add API key input)

**UI Components:**
- API key input field with show/hide toggle
- Usage meter (progress bar showing soft/hard cap)
- Recent requests table
- Copy button for API key

---

#### Phase 10: WOW Demo - Multilingual Panel
**Goal:** Impressive demo showing 4 agents, 2 rounds, 8 turns

**Tasks:**
- [ ] Create `/sandbox/panel` page
- [ ] Implement 4-agent orchestration (OpenAI, Mistral, OpenAI, Mistral)
- [ ] Add multilingual prompts (English, Spanish, Japanese, Arabic)
- [ ] Real-time transcript with agent badges
- [ ] Stats visualization (latency, cost, fallback)

**Files to Create:**
- `src/static/panel.html`
- `src/routes/panel_demo.py` (optional backend orchestration)

**Demo Flow:**
1. User enters initial prompt
2. Agent 1 (OpenAI) responds in English
3. Agent 2 (Mistral) responds in Spanish
4. Agent 3 (OpenAI) responds in Japanese
5. Agent 4 (Mistral) responds in Arabic
6. Round 2: Repeat with follow-up
7. Display full transcript with stats

---

#### Phase 11: Testing
**Goal:** Comprehensive test coverage

**Tasks:**
- [ ] Unit tests for cost_service
- [ ] Unit tests for usage_metering_service
- [ ] Integration tests for auth middleware
- [ ] Integration tests for /usage/me endpoint
- [ ] Manual testing checklist

**Files to Create:**
- `tests/unit/test_cost_service.py`
- `tests/unit/test_usage_metering.py`
- `tests/integration/test_auth.py`
- `tests/integration/test_usage_endpoint.py`
- `tests/MANUAL_TEST_CHECKLIST.md`

**Test Coverage Goals:**
- Cost calculation: 100%
- Auth middleware: 90%
- Usage metering: 90%
- Overall: 80%+

---

#### Phase 12: Deployment
**Goal:** Deploy to production and run acceptance tests

**Tasks:**
- [ ] Run database migrations on production
- [ ] Set environment variables in Render
- [ ] Deploy backend changes
- [ ] Deploy frontend changes
- [ ] Run smoke tests
- [ ] Run acceptance tests

**Environment Variables to Set:**
- `DATABASE_URL` - PostgreSQL connection string
- `BRIKK_REQUIRE_AUTH=true` - Enable auth in production
- `BRIKK_ENCRYPTION_KEY` - Fernet key for API key encryption
- `SENTRY_DSN` - Sentry error tracking
- `CORS_ALLOWED_ORIGINS` - Production domains only

**Acceptance Tests:**
1. Health check returns 200
2. Unauthenticated request returns 401
3. Valid API key returns 200
4. Rate limit enforced after N requests
5. Hard cap blocks requests
6. Usage endpoint returns correct data
7. Circuit breaker opens after failures

---

#### Phase 13: Proof Pack & Delivery
**Goal:** Comprehensive documentation and demo

**Tasks:**
- [ ] Create README with setup instructions
- [ ] Create TECHNICAL_DOCS with architecture
- [ ] Capture screenshots of all features
- [ ] Record demo video (optional)
- [ ] Create proof pack tarball

**Files to Create:**
- `proof-pack/README.md`
- `proof-pack/TECHNICAL_DOCS.md`
- `proof-pack/ARCHITECTURE.md`
- `proof-pack/screenshots/`
- `proof-pack/test-results/`

**Deliverables:**
- Tarball with all documentation
- Screenshots of playground, keys page, panel demo
- Test results (unit + integration)
- Deployment checklist
- API documentation link

---

## Next Steps

1. **Immediate:** Implement Phase 4 (Resilience)
2. **High Priority:** Phases 5, 7, 8 (Security, OpenAPI, Endpoints)
3. **Medium Priority:** Phases 6, 9 (Observability, Frontend)
4. **Nice to Have:** Phase 10 (WOW Demo)
5. **Final:** Phases 11, 12, 13 (Testing, Deployment, Delivery)

**Estimated Time Remaining:** 4-6 hours

---

## Questions for User

1. **Database:** Do you have a PostgreSQL database set up in Render, or do we need to provision one?
2. **API Keys:** Do you want me to create a test API key for development?
3. **WOW Demo:** Is the multilingual panel (Phase 10) a must-have, or can we defer it?
4. **Sentry:** Do you have a Sentry account, or should we skip error tracking for now?
5. **Priority:** Any phases you want to skip or deprioritize?

