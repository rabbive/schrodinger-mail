"""Shared fixtures for the quantum-email-client test suite."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def _isolate_database(monkeypatch, tmp_path):
    """Every test gets its own SQLite database so tests never interfere."""
    import database as db
    import config as cfg

    db_path = tmp_path / "test_email.db"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionFactory", None)
    monkeypatch.setattr(cfg, "DB_PATH", db_path)
    monkeypatch.setattr(cfg, "DATABASE_URL", db_url)
    db.init_db()
    yield
