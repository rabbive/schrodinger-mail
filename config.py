#!/usr/bin/env python3
"""
config.py — Application Configuration
=======================================
Centralised settings loaded from environment variables with sensible defaults.
"""

import os
from pathlib import Path

# ── Core ─────────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("QEC_SECRET_KEY", "dev-secret-change-in-production")
JWT_SECRET = os.environ.get("QEC_JWT_SECRET", SECRET_KEY)
DEBUG = os.environ.get("QEC_DEBUG", "0") == "1"
# Heroku injects PORT dynamically. QEC_PORT remains the local-development override.
PORT = int(os.environ.get("PORT", os.environ.get("QEC_PORT", "5001")))
COOKIE_SECURE = os.environ.get("QEC_COOKIE_SECURE", "0") == "1"

# ── Database ─────────────────────────────────────────────────────────────────
DB_PATH = Path(os.environ.get("QEC_DB_PATH", str(Path(__file__).parent / "quantum_email.db")))
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{DB_PATH}",
)
# Heroku historically supplied postgres:// URLs; SQLAlchemy 2 expects postgresql://.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

# ── Input limits ─────────────────────────────────────────────────────────────
MAX_SUBJECT_LEN = 500
MAX_BODY_LEN = 50_000
MAX_USERNAME_LEN = 32
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25 MB

# ── Rate limits ──────────────────────────────────────────────────────────────
RATE_LIMIT_DEFAULT = "200/minute"
RATE_LIMIT_SEND = "10/minute"
RATE_LIMIT_RECEIVE = "30/minute"
RATE_LIMIT_REGISTER = "3/hour"
RATE_LIMIT_LOGIN = "5/minute"

# ── Feature flags ────────────────────────────────────────────────────────────
UNDO_SEND_SECONDS = 5
DRAFT_AUTOSAVE_SECONDS = 30
ZERO_KNOWLEDGE_MODE = os.environ.get("QEC_ZK_MODE", "0") == "1"
FORWARD_SECRECY = os.environ.get("QEC_FORWARD_SECRECY", "0") == "1"

# Public demo mode seeds Alice/Bob and allows passwordless demo entry. Its reset
# option intentionally keeps Heroku hosting stateless, clean, and add-on free.
DEMO_MODE = os.environ.get("QEC_DEMO_MODE", "0") == "1"
DEMO_USERS = tuple(
    name.strip().lower()
    for name in os.environ.get("QEC_DEMO_USERS", "alice,bob").split(",")
    if name.strip()
)
RESET_DEMO_ON_START = os.environ.get("QEC_RESET_DEMO_ON_START", "0") == "1"
REQUIRE_AUTH = os.environ.get("QEC_REQUIRE_AUTH", "0") == "1"
ALLOW_REGISTRATION = os.environ.get("QEC_ALLOW_REGISTRATION", "1") == "1"

# ── SMTP Gateway ─────────────────────────────────────────────────────────────
SMTP_HOST = os.environ.get("QEC_SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("QEC_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("QEC_SMTP_USER", "")
SMTP_PASS = os.environ.get("QEC_SMTP_PASS", "")
SMTP_USE_TLS = os.environ.get("QEC_SMTP_TLS", "1") == "1"
IMAP_HOST = os.environ.get("QEC_IMAP_HOST", "")
IMAP_PORT = int(os.environ.get("QEC_IMAP_PORT", "993"))

# ── Observability ────────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("QEC_LOG_LEVEL", "INFO")
LOG_FORMAT = os.environ.get("QEC_LOG_FORMAT", "json")  # "json" or "text"
METRICS_ENABLED = os.environ.get("QEC_METRICS", "0") == "1"

# ── P2P LAN Mode ─────────────────────────────────────────────────────────────

# When enabled, each node can accept encrypted messages directly from peers
# on the local network via a small HTTP endpoint.
P2P_ENABLED = os.environ.get("QEC_P2P_ENABLED", "0") == "1"
P2P_LISTEN_PORT = int(os.environ.get("QEC_P2P_PORT", "6001"))
