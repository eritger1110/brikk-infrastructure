# -*- coding: utf-8 -*-
"""
Security headers middleware for Brikk API responses.

Adds security headers to all API responses:
- Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
- X-Content-Type-Options: nosniff
- Referrer-Policy: no-referrer
"""

from functools import wraps
from typing import Callable, Any

from flask import Response, make_response


def add_security_headers(response: Response) -> Response:
    """
    Add security headers to a Flask response.

    Args:
        response: Flask Response object

    Returns:
        Response object with security headers added
    """
    # Strict Transport Security - enforce HTTPS for 1 year
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # Don't send referrer information
    response.headers['Referrer-Policy'] = 'no-referrer'

    return response


def security_headers(f: Callable) -> Callable:
    """
    Decorator that adds security headers to response.

    Can be applied to individual route functions.
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        response = f(*args, **kwargs)

        # Convert to Response object if needed
        if not isinstance(response, Response):
            response = make_response(response)

        return add_security_headers(response)

    return decorated_function


def apply_security_headers_to_blueprint(blueprint) -> None:
    """
    Apply security headers to all responses from a blueprint.

    This is the recommended approach for applying headers to all routes
    in a blueprint without decorating individual functions.
    """
    @blueprint.after_request
    def after_request(response: Response) -> Response:
        return add_security_headers(response)


def apply_security_headers_to_app(app) -> None:
    """
    Apply security headers to all responses from the Flask app.

    This applies headers globally to all routes.
    """
    @app.after_request
    def after_request(response: Response) -> Response:
        return add_security_headers(response)
