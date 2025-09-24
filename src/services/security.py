import os, re, uuid
from functools import wraps
from flask import request, g
from werkzeug.exceptions import Unauthorized, Forbidden

FF_RBAC = os.getenv("FF_RBAC", "0") == "1"
SENSITIVE_KEYS = re.compile(r"(password|secret|api[-_]?key|token|ssn|card)", re.I)

def attach_request_id(app):
    @app.before_request
    def _rid():
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

def redact_dict(d: dict):
    if not isinstance(d, dict): 
        return d
    r = {}
    for k, v in (d or {}).items():
        r[k] = "***" if SENSITIVE_KEYS.search(k or "") else v
    return r

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not getattr(g, "user", None):
            raise Unauthorized("Auth required")
        return f(*args, **kwargs)
    return wrapper

def require_perm(perm_key):
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not FF_RBAC:
                return f(*args, **kwargs)  # gated off for now
            raise Forbidden("Insufficient permissions")
        return wrapper
    return deco
