# Brikk Python SDK

Official Python SDK for the Brikk AI-to-AI infrastructure platform.

## Installation

```bash
pip install brikk
```

Or install from source:

```bash
cd sdk/python
pip install -e .
```

## Quick Start

```python
from brikk import BrikkClient

# Initialize client
client = BrikkClient(
    base_url="https://api.getbrikk.com",
    api_key="your-api-key",
    signing_secret="your-signing-secret"  # For HMAC auth
)

# Check health
health = client.health.ping()
print(health['status'])  # 'ok'

# List agents
agents = client.agents.list(org_id="org_123")
for agent in agents:
    print(f"Agent: {agent['name']}")

# Send coordination message
receipt = client.coordination.send_message(
    sender_id="agent_1",
    recipient_id="agent_2",
    payload={"action": "process", "data": {...}}
)

# Check balance
balance = client.economy.get_balance("org_123")
print(f"Balance: {balance} credits")

# Get reputation
summary = client.reputation.get_summary("org_123")
print(f"Average score: {summary['average_score']}")
```

## Configuration

The SDK can be configured via constructor arguments or environment variables:

- `BRIKK_BASE_URL` - API base URL (default: `http://localhost:8000`)
- `BRIKK_API_KEY` - API key for authentication
- `BRIKK_SIGNING_SECRET` - Signing secret for HMAC authentication
- `BRIKK_ORG_ID` - Default organization ID

## Authentication

The SDK supports two authentication methods:

### 1. API Key (Bearer Token)

```python
client = BrikkClient(api_key="your-api-key")
```

### 2. HMAC Signature (for coordination endpoints)

```python
client = BrikkClient(
    api_key="your-key-id",
    signing_secret="your-signing-secret"
)
```

## Error Handling

The SDK raises typed exceptions for different error conditions:

```python
from brikk import BrikkClient, AuthError, RateLimitError, ServerError

client = BrikkClient()

try:
    agents = client.agents.list(org_id="org_123")
except AuthError as e:
    print(f"Authentication failed: {e.message}")
except RateLimitError as e:
    print(f"Rate limited: {e.message}")
except ServerError as e:
    print(f"Server error: {e.message}")
```

## API Reference

### Health

- `client.health.ping()` - Check API health
- `client.health.readiness()` - Check API readiness
- `client.health.coordination_health()` - Check coordination service health

### Agents

- `client.agents.list(org_id)` - List all agents
- `client.agents.create(name, org_id, metadata)` - Create new agent
- `client.agents.get(agent_id)` - Get agent by ID

### Coordination

- `client.coordination.send_message(sender_id, recipient_id, payload, ...)` - Send inter-agent message

### Economy

- `client.economy.get_balance(org_id)` - Get credit balance
- `client.economy.create_transaction(org_id, type, amount, ...)` - Create transaction

### Reputation

- `client.reputation.get_summary(org_id)` - Get reputation summary
- `client.reputation.list_agent_scores(org_id)` - List agent scores
- `client.reputation.get_agent_score(agent_id)` - Get specific agent score

## Development

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Generate documentation:

```bash
pip install -e ".[docs]"
pdoc brikk -o docs/
```

## License

MIT

