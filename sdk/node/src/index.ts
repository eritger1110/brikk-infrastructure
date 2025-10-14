/**
 * Brikk Node.js SDK
 *
 * Official Node.js SDK for the Brikk AI-to-AI infrastructure platform.
 *
 * @packageDocumentation
 */

export { BrikkClient, type BrikkClientConfig } from './client.js';
export {
  BrikkError,
  HTTPError,
  AuthError,
  RateLimitError,
  ServerError,
  ValidationError,
  NotFoundError,
  TimeoutError,
} from './errors.js';
export type { Agent } from './resources/agents.js';
export type { CoordinationMessage } from './resources/coordination.js';
export type { Transaction } from './resources/economy.js';
export type { HealthStatus } from './resources/health.js';
export type { ReputationScore } from './resources/reputation.js';

