# -*- coding: utf-8 -*-
"""Exception classes for the Brikk SDK."""


class BrikkError(Exception):
    """Base exception for all Brikk SDK errors."""

    def __init__(self, message: str, status_code: int = None, response=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class HTTPError(BrikkError):
    """Raised when an HTTP request fails."""
    pass


class AuthError(BrikkError):
    """Raised when authentication fails (401/403)."""
    pass


class RateLimitError(BrikkError):
    """Raised when rate limit is exceeded (429)."""
    pass


class ServerError(BrikkError):
    """Raised when server returns 5xx error."""
    pass


class ValidationError(BrikkError):
    """Raised when request validation fails (400)."""
    pass


class NotFoundError(BrikkError):
    """Raised when resource is not found (404)."""
    pass


class TimeoutError(BrikkError):
    """Raised when request times out."""
    pass

