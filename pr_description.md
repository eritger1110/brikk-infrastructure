## Stage 4: Production-Ready SDKs (Python & Node.js)

This PR introduces production-ready SDKs for Python and Node.js, complete with CI/CD, documentation, smoke tests, and quickstarts, all while adhering to strict regression-proof guidelines.

### ✅ Deliverables

1.  **Python SDK (`brikk==0.1.0`)**
    - Location: `sdk/python/`
    - Features: Sync/async support, typed errors, HMAC auth, retry logic.
    - Tests: `sdk/python/tests/` (12 passed, 1 skipped)

2.  **Node.js SDK (`@brikk/sdk@0.1.0`)**
    - Location: `sdk/node/`
    - Features: TypeScript, typed errors, HMAC auth, retry logic.
    - Tests: `sdk/node/test/` (12 passed)

3.  **CI/CD Workflows**
    - Python: `.github/workflows/sdk-python.yml`
    - Node.js: `.github/workflows/sdk-node.yml`
    - Features: Multi-version testing, linting, docs generation, manual publish.

4.  **Quickstart Examples**
    - Python: `examples/sdk/python_quickstart.py`
    - Node.js: `examples/sdk/node_quickstart.ts`

5.  **API Documentation**
    - Generated docs for both SDKs are uploaded as CI artifacts.
    - Index: `docs/sdk/README.md`

6.  **Comprehensive Tests**
    - **Contract Test**: `tests/test_sdk_contract.py` ensures all SDK-used endpoints exist.
    - **Regression Check**: All existing repository tests pass, verifying no server-side changes were made.

### 🔒 Regression-Proof Addendum Compliance

- **No Server Code Changes**: All changes are confined to `sdk/`, `docs/sdk/`, `.github/workflows/`, and a new contract test in `tests/`.
- **Existing CI Green**: The PR will pass all existing workflows (`test`, `examples`, `ascii-lint`).
- **Backwards-Compatible API Usage**: SDKs only call endpoints already present in `src/routes/**`.
- **Non-Destructive Smoke Tests**: All mutating calls in tests are mocked.
- **Branch Protection Ready**: The PR will require `sdk-python` and `sdk-node` status checks to pass.
- **Release-Safe**: Publishing is a manual `workflow_dispatch` action only.

### Endpoints Touched

- `GET /healthz`
- `GET /readyz`
- `GET /api/v1/agents`
- `POST /api/v1/agents`
- `GET /api/v1/agents/{id}`
- `POST /api/v1/coordination`
- `GET /api/v1/coordination/health`
- `GET /api/v1/economy/balance`
- `POST /api/v1/economy/transaction`
- `GET /api/v1/reputation/summary`
- `GET /api/v1/reputation/agents`

This implementation provides a robust, well-tested, and documented foundation for developers to build on the Brikk platform.

