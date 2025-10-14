/**
 * Exception classes for the Brikk SDK.
 */

export class BrikkError extends Error {
  public readonly statusCode?: number;
  public readonly response?: Response;

  constructor(message: string, statusCode?: number, response?: Response) {
    super(message);
    this.name = this.constructor.name;
    this.statusCode = statusCode;
    this.response = response;
    Error.captureStackTrace(this, this.constructor);
  }
}

export class HTTPError extends BrikkError {}

export class AuthError extends BrikkError {}

export class RateLimitError extends BrikkError {}

export class ServerError extends BrikkError {}

export class ValidationError extends BrikkError {}

export class NotFoundError extends BrikkError {}

export class TimeoutError extends BrikkError {}

