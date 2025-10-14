/**
 * Smoke tests for the Brikk SDK.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrikkClient } from '../src/client.js';
import { AuthError } from '../src/errors.js';

describe('BrikkClient', () => {
  it('should initialize with default config', () => {
    const client = new BrikkClient();
    expect(client.baseUrl).toBeDefined();
    expect(client.health).toBeDefined();
    expect(client.agents).toBeDefined();
    expect(client.coordination).toBeDefined();
    expect(client.economy).toBeDefined();
    expect(client.reputation).toBeDefined();
  });

  it('should initialize with custom config', () => {
    const client = new BrikkClient({
      baseUrl: 'https://api.example.com',
      apiKey: 'test-key',
    });
    expect(client.baseUrl).toBe('https://api.example.com');
    expect(client.apiKey).toBe('test-key');
  });

  it('should initialize from environment variables', () => {
    process.env.BRIKK_BASE_URL = 'https://env.example.com';
    process.env.BRIKK_API_KEY = 'env-key';
    
    const client = new BrikkClient();
    expect(client.baseUrl).toBe('https://env.example.com');
    expect(client.apiKey).toBe('env-key');
    
    delete process.env.BRIKK_BASE_URL;
    delete process.env.BRIKK_API_KEY;
  });
});

describe('Health Resource', () => {
  it('should call health ping (mocked)', async () => {
    const client = new BrikkClient({ baseUrl: 'http://localhost:8000', apiKey: 'test' });
    
    // Mock the HTTP client
    vi.spyOn(client['_http'], 'get').mockResolvedValue({ status: 'ok' });
    
    const result = await client.health.ping();
    expect(result.status).toBe('ok');
  });
});

describe('Agents Resource', () => {
  it('should list agents (mocked)', async () => {
    const client = new BrikkClient({ baseUrl: 'http://localhost:8000', apiKey: 'test' });
    
    const mockAgents = [
      { id: 'agent_1', name: 'Agent 1', org_id: 'org_123' },
      { id: 'agent_2', name: 'Agent 2', org_id: 'org_123' },
    ];
    
    vi.spyOn(client['_http'], 'get').mockResolvedValue({ agents: mockAgents });
    
    const agents = await client.agents.list('org_123');
    expect(agents).toHaveLength(2);
    expect(agents[0].name).toBe('Agent 1');
  });

  it('should create agent (mocked)', async () => {
    const client = new BrikkClient({ baseUrl: 'http://localhost:8000', apiKey: 'test' });
    
    const mockAgent = { id: 'agent_new', name: 'New Agent', org_id: 'org_123' };
    
    vi.spyOn(client['_http'], 'post').mockResolvedValue(mockAgent);
    
    const agent = await client.agents.create('New Agent', 'org_123');
    expect(agent.id).toBe('agent_new');
    expect(agent.name).toBe('New Agent');
  });
});

describe('Economy Resource', () => {
  it('should get balance (mocked)', async () => {
    const client = new BrikkClient({ baseUrl: 'http://localhost:8000', apiKey: 'test' });
    
    vi.spyOn(client['_http'], 'get').mockResolvedValue({ balance: 1000 });
    
    const balance = await client.economy.getBalance('org_123');
    expect(balance).toBe(1000);
  });

  it('should create transaction (mocked)', async () => {
    const client = new BrikkClient({ baseUrl: 'http://localhost:8000', apiKey: 'test' });
    
    const mockTx = {
      id: 'tx_123',
      org_id: 'org_123',
      type: 'credit',
      amount: 100,
      meta: {},
      created_at: new Date().toISOString(),
    };
    
    vi.spyOn(client['_http'], 'post').mockResolvedValue(mockTx);
    
    const tx = await client.economy.createTransaction('org_123', 'credit', 100);
    expect(tx.amount).toBe(100);
  });
});

describe('Reputation Resource', () => {
  it('should get summary (mocked)', async () => {
    const client = new BrikkClient({ baseUrl: 'http://localhost:8000', apiKey: 'test' });
    
    const mockSummary = {
      average_score: 4.5,
      total_agents: 10,
      total_interactions: 500,
    };
    
    vi.spyOn(client['_http'], 'get').mockResolvedValue(mockSummary);
    
    const summary = await client.reputation.getSummary('org_123');
    expect(summary.average_score).toBe(4.5);
  });

  it('should list agent scores (mocked)', async () => {
    const client = new BrikkClient({ baseUrl: 'http://localhost:8000', apiKey: 'test' });
    
    const mockScores = [
      { agent_id: 'agent_1', score: 4.5, total_interactions: 100, positive_feedback: 90, negative_feedback: 10 },
      { agent_id: 'agent_2', score: 4.8, total_interactions: 200, positive_feedback: 190, negative_feedback: 10 },
    ];
    
    vi.spyOn(client['_http'], 'get').mockResolvedValue({ agents: mockScores });
    
    const scores = await client.reputation.listAgentScores('org_123');
    expect(scores).toHaveLength(2);
    expect(scores[0].score).toBe(4.5);
  });
});

describe('Coordination Resource', () => {
  it('should send message (mocked)', async () => {
    const client = new BrikkClient({
      baseUrl: 'http://localhost:8000',
      apiKey: 'test-key',
      signingSecret: 'test-secret',
    });
    
    const mockReceipt = {
      message_id: 'msg_123',
      status: 'delivered',
      timestamp: new Date().toISOString(),
    };
    
    vi.spyOn(client['_http'], 'post').mockResolvedValue(mockReceipt);
    
    const receipt = await client.coordination.sendMessage(
      'agent_1',
      'agent_2',
      { test: 'data' }
    );
    expect(receipt.status).toBe('delivered');
  });
});

describe('Error Handling', () => {
  it('should throw AuthError on 401', async () => {
    const client = new BrikkClient({ baseUrl: 'http://localhost:8000', apiKey: 'test' });
    
    vi.spyOn(client['_http'], 'get').mockRejectedValue(new AuthError('Unauthorized', 401));
    
    await expect(client.health.ping()).rejects.toThrow(AuthError);
  });
});

