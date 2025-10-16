"""
Unified logging infrastructure module.

This module provides a single, standardized entry point for all logging
configuration across the application.
"""

from src.services.structured_logging import (
    configure_logging,
    init_logging,
    get_logger,
)

# Export logging utilities
__all__ = ["configure_logging", "init_logging", "get_logger"]

