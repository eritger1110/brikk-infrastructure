"""
Infrastructure package - unified entry points for core services.

This package provides standardized, centralized access to:
- Database (db)
- Authentication (require_scope)
- Logging (configure_logging, init_logging, get_logger)
"""

from src.infra.db import db
from src.infra.auth import require_scope
from src.infra.log import configure_logging, init_logging, get_logger

__all__ = [
    "db",
    "require_scope",
    "configure_logging",
    "init_logging",
    "get_logger",
]

