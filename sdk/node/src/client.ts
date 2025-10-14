/**
 * Main Brikk SDK client.
 */

import { HTTPClient } from './http.js';
import { AgentsResource } from './resources/agents.js';
import { CoordinationResource } from './resources/coordination.js';
import { EconomyResource } from './resources/economy.js';
import { HealthResource } from './resources/health.js';
import { ReputationResource } from './resources/reputation.js';

export interface BrikkClientConfig {
  baseUrl?: string;
  apiKey?: string;
  signingSecret?: string;
  orgId?: string;
  timeoutMs?: number;
  maxRetries?: number;
}

/**
 * Brikk API client.
 *
 * The main entry point for interacting with the Brikk platform.
 *
 * @example
 * ```typescript
 * import { BrikkClient } from '@brikk/sdk';
 *
 * const client = new BrikkClient({
 *   baseUrl: 'https://api.getbrikk.com',
 *   apiKey: 'your-api-key'
 * });
 *
 * const health = await client.health.ping();
 * console.log(health.status);
 * ```
 */
export class BrikkClient {
  public readonly baseUrl: string;
  public readonly apiKey?: string;
  public readonly signingSecret?: string;
  public readonly orgId?: string;
  public readonly timeoutMs: number;
  public readonly maxRetries: number;

  private readonly _http: HTTPClient;

  public readonly health: HealthResource;
  public readonly agents: AgentsResource;
  public readonly coordination: CoordinationResource;
  public readonly economy: EconomyResource;
  public readonly reputation: ReputationResource;

  constructor(config: BrikkClientConfig = {}) {
    this.baseUrl = config.baseUrl || process.env.BRIKK_BASE_URL || 'http://localhost:8000';
    this.apiKey = config.apiKey || process.env.BRIKK_API_KEY;
    this.signingSecret = config.signingSecret || process.env.BRIKK_SIGNING_SECRET;
    this.orgId = config.orgId || process.env.BRIKK_ORG_ID;
    this.timeoutMs = config.timeoutMs || 30000;
    this.maxRetries = config.maxRetries || 3;

    this._http = new HTTPClient({
      baseUrl: this.baseUrl,
      apiKey: this.apiKey,
      signingSecret: this.signingSecret,
      timeoutMs: this.timeoutMs,
      maxRetries: this.maxRetries,
    });

    this.health = new HealthResource(this._http);
    this.agents = new AgentsResource(this._http);
    this.coordination = new CoordinationResource(this._http);
    this.economy = new EconomyResource(this._http);
    this.reputation = new ReputationResource(this._http);
  }
}

