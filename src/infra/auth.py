"""
Unified authentication infrastructure module.

This module provides a single, standardized entry point for all authentication
decorators across the application. All routes should import from here.
"""

from src.services.auth_middleware import require_scope

# Export official auth decorators
__all__ = ["require_scope"]

