# @brikk/sdk

Official Node.js SDK for the Brikk AI-to-AI infrastructure platform.

## Installation

```bash
npm install @brikk/sdk
```

Or with pnpm:

```bash
pnpm add @brikk/sdk
```

## Quick Start

```typescript
import { BrikkClient } from '@brikk/sdk';

// Initialize client
const client = new BrikkClient({
  baseUrl: 'https://api.getbrikk.com',
  apiKey: 'your-api-key',
  signingSecret: 'your-signing-secret', // For HMAC auth
});

// Check health
const health = await client.health.ping();
console.log(health.status); // 'ok'

// List agents
const agents = await client.agents.list('org_123');
for (const agent of agents) {
  console.log(`Agent: ${agent.name}`);
}

// Send coordination message
const receipt = await client.coordination.sendMessage(
  'agent_1',
  'agent_2',
  { action: 'process', data: {...} }
);

// Check balance
const balance = await client.economy.getBalance('org_123');
console.log(`Balance: ${balance} credits`);

// Get reputation
const summary = await client.reputation.getSummary('org_123');
console.log(`Average score: ${summary.average_score}`);
```

## Configuration

The SDK can be configured via constructor options or environment variables:

- `BRIKK_BASE_URL` - API base URL (default: `http://localhost:8000`)
- `BRIKK_API_KEY` - API key for authentication
- `BRIKK_SIGNING_SECRET` - Signing secret for HMAC authentication
- `BRIKK_ORG_ID` - Default organization ID

## Authentication

The SDK supports two authentication methods:

### 1. API Key (Bearer Token)

```typescript
const client = new BrikkClient({ apiKey: 'your-api-key' });
```

### 2. HMAC Signature (for coordination endpoints)

```typescript
const client = new BrikkClient({
  apiKey: 'your-key-id',
  signingSecret: 'your-signing-secret',
});
```

## Error Handling

The SDK throws typed errors for different error conditions:

```typescript
import { BrikkClient, AuthError, RateLimitError, ServerError } from '@brikk/sdk';

const client = new BrikkClient();

try {
  const agents = await client.agents.list('org_123');
} catch (error) {
  if (error instanceof AuthError) {
    console.error('Authentication failed:', error.message);
  } else if (error instanceof RateLimitError) {
    console.error('Rate limited:', error.message);
  } else if (error instanceof ServerError) {
    console.error('Server error:', error.message);
  }
}
```

## API Reference

### Health

- `client.health.ping()` - Check API health
- `client.health.readiness()` - Check API readiness
- `client.health.coordinationHealth()` - Check coordination service health

### Agents

- `client.agents.list(orgId)` - List all agents
- `client.agents.create(name, orgId, metadata)` - Create new agent
- `client.agents.get(agentId)` - Get agent by ID

### Coordination

- `client.coordination.sendMessage(senderId, recipientId, payload, ...)` - Send inter-agent message

### Economy

- `client.economy.getBalance(orgId)` - Get credit balance
- `client.economy.createTransaction(orgId, type, amount, ...)` - Create transaction

### Reputation

- `client.reputation.getSummary(orgId)` - Get reputation summary
- `client.reputation.listAgentScores(orgId)` - List agent scores
- `client.reputation.getAgentScore(agentId)` - Get specific agent score

## TypeScript

This SDK is written in TypeScript and includes full type definitions. All methods and responses are fully typed for the best development experience.

## Development

Install dependencies:

```bash
pnpm install
```

Build the SDK:

```bash
pnpm build
```

Run tests:

```bash
pnpm test
```

Generate documentation:

```bash
pnpm docs
```

## License

MIT

