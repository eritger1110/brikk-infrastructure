/**
 * Reputation and scoring resources.
 */

import { HTTPClient } from '../http.js';

export interface ReputationScore {
  agent_id: string;
  score: number;
  total_interactions: number;
  positive_feedback: number;
  negative_feedback: number;
}

export class ReputationResource {
  constructor(private http: HTTPClient) {}

  /**
   * Get reputation summary for an organization.
   */
  async getSummary(orgId: string): Promise<Record<string, any>> {
    return this.http.get('/api/v1/reputation/summary', { org_id: orgId });
  }

  /**
   * List reputation scores for all agents in an organization.
   */
  async listAgentScores(orgId: string): Promise<ReputationScore[]> {
    const response = await this.http.get<{ agents: ReputationScore[] }>(
      '/api/v1/reputation/agents',
      { org_id: orgId }
    );
    return response.agents || [];
  }

  /**
   * Get reputation score for a specific agent.
   */
  async getAgentScore(agentId: string, orgId?: string): Promise<ReputationScore | null> {
    const params: Record<string, any> = { agent_id: agentId };
    if (orgId) {
      params.org_id = orgId;
    }
    const response = await this.http.get<{ agents: ReputationScore[] }>(
      '/api/v1/reputation/agents',
      params
    );
    const agents = response.agents || [];
    return agents.find(a => a.agent_id === agentId) || null;
  }
}

