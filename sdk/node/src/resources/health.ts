/**
 * Health check resources.
 */

import { HTTPClient } from '../http.js';

export interface HealthStatus {
  status: string;
  timestamp?: string;
  version?: string;
}

export class HealthResource {
  constructor(private http: HTTPClient) {}

  /**
   * Check if the API is responsive.
   */
  async ping(): Promise<HealthStatus> {
    return this.http.get<HealthStatus>('/healthz');
  }

  /**
   * Check if the API is ready to serve requests.
   */
  async readiness(): Promise<HealthStatus> {
    return this.http.get<HealthStatus>('/readyz');
  }

  /**
   * Check coordination service health.
   */
  async coordinationHealth(): Promise<HealthStatus> {
    return this.http.get<HealthStatus>('/api/v1/coordination/health');
  }
}

