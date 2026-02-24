#!/usr/bin/env python3
"""
config.py — Application Configuration
=======================================
Centralised settings loaded from environment variables with sensible defaults.
"""

import os

SECRET_KEY = os.environ.get("QEC_SECRET_KEY", "dev-secret-change-in-production")
DEBUG = os.environ.get("QEC_DEBUG", "0") == "1"
PORT = int(os.environ.get("QEC_PORT", "5001"))

MAX_SUBJECT_LEN = 500
MAX_BODY_LEN = 50_000
MAX_USERNAME_LEN = 32
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25 MB

RATE_LIMIT_SEND = "10/minute"
RATE_LIMIT_RECEIVE = "30/minute"
RATE_LIMIT_REGISTER = "3/hour"
RATE_LIMIT_LOGIN = "5/minute"

UNDO_SEND_SECONDS = 5
DRAFT_AUTOSAVE_SECONDS = 30
