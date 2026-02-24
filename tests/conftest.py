"""Shared fixtures for the quantum-email-client test suite."""

import os
import sys
import tempfile

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def _isolate_database(monkeypatch, tmp_path):
    """Every test gets its own SQLite database so tests never interfere."""
    import database as db

    db_path = tmp_path / "test_email.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    # Reset cached connection so the next call opens the temp DB
    monkeypatch.setattr(db, "_conn", None)
    db.init_db()
    yield
    # Close connection after test
    if db._conn is not None:
        try:
            db._conn.close()
        except Exception:
            pass
        db._conn = None
