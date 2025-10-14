/**
 * Coordination and messaging resources.
 */

import { randomUUID } from 'crypto';
import { HTTPClient } from '../http.js';

export interface CoordinationMessage {
  version: string;
  message_id: string;
  ts: string;
  type: string;
  sender: { agent_id: string };
  recipient: { agent_id: string };
  payload: Record<string, any>;
  ttl_ms: number;
}

export class CoordinationResource {
  constructor(private http: HTTPClient) {}

  /**
   * Send a coordination message between agents.
   */
  async sendMessage(
    senderId: string,
    recipientId: string,
    payload: Record<string, any>,
    messageType = 'event',
    ttlMs = 60000
  ): Promise<any> {
    const message: CoordinationMessage = {
      version: '1.0',
      message_id: randomUUID(),
      ts: new Date().toISOString(),
      type: messageType,
      sender: { agent_id: senderId },
      recipient: { agent_id: recipientId },
      payload,
      ttl_ms: ttlMs,
    };
    return this.http.post('/api/v1/coordination', message, true);
  }
}

