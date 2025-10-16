"""
Unified database infrastructure module.

This module provides a single, standardized entry point for all database
operations across the application. All models should import from here.
"""

from src.database import db

# Export the main SQLAlchemy instance
__all__ = ["db"]

