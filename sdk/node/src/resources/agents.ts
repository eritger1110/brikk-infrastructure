/**
 * Agent management resources.
 */

import { HTTPClient } from '../http.js';

export interface Agent {
  id: string;
  name: string;
  org_id: string;
  created_at?: string;
  updated_at?: string;
}

export class AgentsResource {
  constructor(private http: HTTPClient) {}

  /**
   * List all agents for an organization.
   */
  async list(orgId?: string): Promise<Agent[]> {
    const params: Record<string, any> = {};
    if (orgId) {
      params.org_id = orgId;
    }
    const response = await this.http.get<{ agents: Agent[] }>('/api/v1/agents', params);
    return response.agents || [];
  }

  /**
   * Create a new agent.
   */
  async create(
    name: string,
    orgId: string,
    metadata?: Record<string, any>
  ): Promise<Agent> {
    const data: any = {
      name,
      org_id: orgId,
    };
    if (metadata) {
      data.metadata = metadata;
    }
    return this.http.post<Agent>('/api/v1/agents', data);
  }

  /**
   * Get agent by ID.
   */
  async get(agentId: string): Promise<Agent> {
    return this.http.get<Agent>(`/api/v1/agents/${agentId}`);
  }
}

