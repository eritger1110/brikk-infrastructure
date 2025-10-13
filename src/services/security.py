# -*- coding: utf-8 -*-
# src/services/security.py
import os
import re
import uuid
from functools import wraps
from types import SimpleNamespace

from flask import request, g, jsonify
from flask_jwt_extended import (
    verify_jwt_in_request,
    get_jwt_identity,
    get_jwt,
)

# Feature flag: turn on real RBAC checks when ready
FF_RBAC = os.getenv("FF_RBAC", "0") == "1"

# Used by redact_dict
SENSITIVE_KEYS = re.compile(
    r"(password|secret|api[-_]?key|token|ssn|card)", re.I)


def attach_request_id(app):
    """Attach a unique request id into flask.g for log correlation."""
    @app.before_request
    def _rid():
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())


def redact_dict(d: dict):
    """Shallow redact of sensitive-looking keys."""
    if not isinstance(d, dict):
        return d
    out = {}
    for k, v in (d or {}).items():
        out[k] = "***" if SENSITIVE_KEYS.search(k or "") else v
    return out


def _load_user_from_identity(identity, claims):
    """
    Map JWT identity/claims into a lightweight user object.
    Replace with a real DB lookup if/when you have a User model.
    """
    # Common patterns:
    #  - identity might be an email or a user id
    #  - custom claims may include org_id, perms, roles, etc.
    org_id = claims.get("org_id")
    perms = set(claims.get("perms", []) or [])
    roles = set(claims.get("roles", []) or [])

    # Simple, attribute-friendly object for g.user
    user = SimpleNamespace(
        id=claims.get("user_id"),     # or None
        email=identity if isinstance(identity, str) else claims.get("email"),
        org_id=org_id,
        permissions=perms,
        roles=roles,
    )
    return user


def _ensure_jwt_loaded():
    """
    Verify a JWT is present (prefer cookies; allow headers too) and
    populate g.user. Returns (ok: bool, response) where response is
    a Flask response to return on failure.
    """
    try:
        # Look in cookies first; allow headers as a fallback.
        verify_jwt_in_request(locations=["cookies", "headers"])
    except Exception:
        return False, jsonify({"error": "auth_required"}), 401

    identity = get_jwt_identity()
    if not identity:
        return False, jsonify({"error": "auth_required"}), 401

    claims = get_jwt() or {}
    g.user = _load_user_from_identity(identity, claims)
    if not g.user:
        return False, jsonify({"error": "auth_required"}), 401

    return True, None, None


def require_auth(fn):
    """
    Decorator: ensures a valid JWT and sets g.user.
    Returns JSON 401 on failure (no HTML error pages).
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        ok, resp, code = _ensure_jwt_loaded()
        if not ok:
            return resp, code
        return fn(*args, **kwargs)
    return wrapper


def require_perm(permission_name: str):
    """
    Decorator: ensures auth and (when FF_RBAC=1) that the user has a permission.
    Looks in g.user.permissions (and also in roles for a simple allow-list).
    """
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ok, resp, code = _ensure_jwt_loaded()
            if not ok:
                return resp, code

            if not FF_RBAC:
                # RBAC disabled: allow all once authenticated
                return fn(*args, **kwargs)

            user = getattr(g, "user", None)
            perms = (getattr(user, "permissions", set()) or set())
            roles = (getattr(user, "roles", set()) or set())

            # Simple model: having the perm in `perms` OR `roles` passes.
            if (permission_name not in perms) and (
                    permission_name not in roles):
                return jsonify(
                    {"error": "forbidden", "missing": permission_name}), 403

            return fn(*args, **kwargs)
        return wrapper
    return deco
