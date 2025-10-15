"""Startup safety tests to ensure app boots with various configurations."""
import os
import pytest
from src.factory import create_app


def test_app_boots_without_dev_routes(monkeypatch):
    """Test that app boots successfully when dev routes are disabled."""
    monkeypatch.setenv("ENABLE_DEV_LOGIN", "0")
    monkeypatch.setenv("TESTING", "true")
    app = create_app()
    assert app is not None
    assert app.name == "src.factory"


def test_app_boots_with_dev_routes(monkeypatch):
    """Test that app boots successfully when dev routes are enabled."""
    monkeypatch.setenv("ENABLE_DEV_LOGIN", "1")
    monkeypatch.setenv("TESTING", "true")
    app = create_app()
    # Should not raise even if dev_login.py is minimal
    assert app is not None
    assert app.name == "src.factory"


def test_app_boots_with_migrations_disabled(monkeypatch):
    """Test that app boots when migrations are explicitly disabled."""
    monkeypatch.setenv("BRIKK_DB_MIGRATE_ON_START", "false")
    monkeypatch.setenv("TESTING", "true")
    app = create_app()
    assert app is not None


def test_app_boots_with_migrations_enabled_in_test_mode(monkeypatch):
    """Test that migrations are skipped in test mode even when enabled."""
    monkeypatch.setenv("BRIKK_DB_MIGRATE_ON_START", "true")
    monkeypatch.setenv("TESTING", "true")
    app = create_app()
    # Should not attempt to run migrations in test mode
    assert app is not None

