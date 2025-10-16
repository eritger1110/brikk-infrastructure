"""
Unified logging infrastructure module.

This module provides a single, standardized entry point for all logging
configuration across the application.
"""

from src.services.structured_logging import setup_logging, get_logger

# Export logging utilities
__all__ = ["setup_logging", "get_logger"]

