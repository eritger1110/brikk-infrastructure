# -*- coding: utf-8 -*-
"""Test that the SDK can be imported correctly."""


def test_import_client():
    """Test importing the main client."""
    from brikk import BrikkClient
    assert BrikkClient is not None


def test_import_errors():
    """Test importing error classes."""
    from brikk import (
        AuthError,
        BrikkError,
        HTTPError,
        NotFoundError,
        RateLimitError,
        ServerError,
        TimeoutError,
        ValidationError,
    )
    assert all([
        BrikkError,
        HTTPError,
        AuthError,
        RateLimitError,
        ServerError,
        ValidationError,
        NotFoundError,
        TimeoutError,
    ])


def test_import_types():
    """Test importing type definitions."""
    from brikk import (
        Agent,
        CoordinationMessage,
        HealthStatus,
        ReputationScore,
        Transaction,
    )
    assert all([
        Agent,
        CoordinationMessage,
        HealthStatus,
        ReputationScore,
        Transaction,
    ])


def test_version():
    """Test that version is defined."""
    import brikk
    assert hasattr(brikk, "__version__")
    assert isinstance(brikk.__version__, str)

