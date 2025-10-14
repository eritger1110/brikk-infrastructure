/**
 * Economy and credits management resources.
 */

import { randomUUID } from 'crypto';
import { HTTPClient } from '../http.js';

export interface Transaction {
  id: string;
  org_id: string;
  type: string;
  amount: number;
  meta: Record<string, any>;
  created_at: string;
}

export class EconomyResource {
  constructor(private http: HTTPClient) {}

  /**
   * Get credit balance for an organization.
   */
  async getBalance(orgId: string): Promise<number> {
    const response = await this.http.get<{ balance: number }>(
      '/api/v1/economy/balance',
      { org_id: orgId }
    );
    return response.balance || 0;
  }

  /**
   * Create a new transaction.
   */
  async createTransaction(
    orgId: string,
    transactionType: string,
    amount: number,
    metadata?: Record<string, any>,
    idempotencyKey?: string
  ): Promise<Transaction> {
    const data = {
      org_id: orgId,
      type: transactionType,
      amount,
      meta: metadata || {},
      idempotency_key: idempotencyKey || randomUUID(),
    };
    return this.http.post<Transaction>('/api/v1/economy/transaction', data);
  }
}

