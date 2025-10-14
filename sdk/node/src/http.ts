/**
 * HTTP client for Brikk SDK with retry logic and error handling.
 */

import { createHmac } from 'crypto';
import {
  AuthError,
  HTTPError,
  NotFoundError,
  RateLimitError,
  ServerError,
  TimeoutError,
  ValidationError,
} from './errors.js';

export interface HTTPClientConfig {
  baseUrl: string;
  apiKey?: string;
  signingSecret?: string;
  timeoutMs?: number;
  maxRetries?: number;
}

export class HTTPClient {
  private baseUrl: string;
  private apiKey?: string;
  private signingSecret?: string;
  private timeoutMs: number;
  private maxRetries: number;

  constructor(config: HTTPClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.apiKey = config.apiKey;
    this.signingSecret = config.signingSecret;
    this.timeoutMs = config.timeoutMs || 30000;
    this.maxRetries = config.maxRetries || 3;
  }

  private buildUrl(path: string): string {
    if (path.startsWith('http')) {
      return path;
    }
    return `${this.baseUrl}/${path.replace(/^\//, '')}`;
  }

  private generateHmacSignature(timestamp: string, body: string): string {
    if (!this.signingSecret) {
      throw new AuthError('Signing secret required for HMAC authentication');
    }
    const message = `${timestamp}.${body}`;
    return createHmac('sha256', this.signingSecret)
      .update(message)
      .digest('hex');
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    let data: any;
    try {
      data = await response.json();
    } catch {
      data = { text: await response.text() };
    }

    if (response.ok) {
      return data as T;
    }

    const errorMsg = data.error || `HTTP ${response.status}`;

    if (response.status === 400) {
      throw new ValidationError(errorMsg, response.status, response);
    } else if (response.status === 401 || response.status === 403) {
      throw new AuthError(errorMsg, response.status, response);
    } else if (response.status === 404) {
      throw new NotFoundError(errorMsg, response.status, response);
    } else if (response.status === 429) {
      throw new RateLimitError(errorMsg, response.status, response);
    } else if (response.status >= 500) {
      throw new ServerError(errorMsg, response.status, response);
    } else {
      throw new HTTPError(errorMsg, response.status, response);
    }
  }

  private async sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async request<T>(
    method: string,
    path: string,
    options: {
      body?: any;
      params?: Record<string, any>;
      headers?: Record<string, string>;
      useHmac?: boolean;
    } = {}
  ): Promise<T> {
    const url = new URL(this.buildUrl(path));
    
    if (options.params) {
      Object.entries(options.params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    const headers: Record<string, string> = options.headers || {};

    // Add authentication headers
    if (options.useHmac && this.signingSecret) {
      const timestamp = Math.floor(Date.now() / 1000).toString();
      const body = options.body ? JSON.stringify(options.body) : '';
      const signature = this.generateHmacSignature(timestamp, body);
      headers['X-Brikk-Key'] = this.apiKey || '';
      headers['X-Brikk-Timestamp'] = timestamp;
      headers['X-Brikk-Signature'] = signature;
    } else if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`;
    }

    if (options.body) {
      headers['Content-Type'] = 'application/json';
    }

    let lastError: Error | null = null;
    
    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

        const response = await fetch(url.toString(), {
          method,
          headers,
          body: options.body ? JSON.stringify(options.body) : undefined,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);
        return await this.handleResponse<T>(response);
      } catch (error: any) {
        lastError = error;

        // Don't retry on client errors (4xx except 429)
        if (error.statusCode && error.statusCode >= 400 && error.statusCode < 500 && error.statusCode !== 429) {
          throw error;
        }

        // Don't retry on last attempt
        if (attempt === this.maxRetries) {
          break;
        }

        // Exponential backoff
        const backoffMs = Math.min(1000 * Math.pow(2, attempt), 10000);
        await this.sleep(backoffMs);
      }
    }

    if (lastError?.name === 'AbortError') {
      throw new TimeoutError(`Request timed out after ${this.timeoutMs}ms`);
    }

    throw lastError || new HTTPError('Request failed');
  }

  async get<T>(path: string, params?: Record<string, any>): Promise<T> {
    return this.request<T>('GET', path, { params });
  }

  async post<T>(path: string, body?: any, useHmac = false): Promise<T> {
    return this.request<T>('POST', path, { body, useHmac });
  }

  async put<T>(path: string, body?: any): Promise<T> {
    return this.request<T>('PUT', path, { body });
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>('DELETE', path);
  }
}

