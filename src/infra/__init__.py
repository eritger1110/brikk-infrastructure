"""
Infrastructure package - unified entry points for core services.

This package provides standardized, centralized access to:
- Database (db)
- Authentication (require_scope)
- Logging (setup_logging, get_logger)
"""

from src.infra.db import db
from src.infra.auth import require_scope
from src.infra.log import setup_logging, get_logger

__all__ = [
    "db",
    "require_scope",
    "setup_logging",
    "get_logger",
]

