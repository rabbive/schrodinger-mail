#!/usr/bin/env python3
"""
auth.py — JWT Authentication
==============================
Provides JWT-based authentication with access + refresh token rotation.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional, Tuple

import config

_JWT_ALG = "HS256"
_ACCESS_TTL = 3600          # 1 hour
_REFRESH_TTL = 86400 * 7    # 7 days

_secret = getattr(config, "JWT_SECRET", None) or config.SECRET_KEY

# Simple set-based token blacklist (use Redis in production)
_blacklist: set[str] = set()


def _b64url_encode(data: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    import base64
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _hmac_sign(payload: str) -> str:
    return _b64url_encode(
        hmac.new(_secret.encode(), payload.encode(), hashlib.sha256).digest()
    )


def create_token(
    username: str,
    token_type: str = "access",
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a JWT token."""
    now = int(time.time())
    ttl = _ACCESS_TTL if token_type == "access" else _REFRESH_TTL
    payload: Dict[str, Any] = {
        "sub": username,
        "type": token_type,
        "iat": now,
        "exp": now + ttl,
        "jti": _b64url_encode(os.urandom(16)),
    }
    if extra:
        payload.update(extra)
    header = _b64url_encode(json.dumps({"alg": _JWT_ALG, "typ": "JWT"}).encode())
    body = _b64url_encode(json.dumps(payload).encode())
    unsigned = f"{header}.{body}"
    sig = _hmac_sign(unsigned)
    return f"{unsigned}.{sig}"


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT. Returns the payload or ``None``."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        unsigned = f"{parts[0]}.{parts[1]}"
        expected_sig = _hmac_sign(unsigned)
        if not hmac.compare_digest(expected_sig, parts[2]):
            return None
        payload = json.loads(_b64url_decode(parts[1]))
        if payload.get("exp", 0) < int(time.time()):
            return None
        if payload.get("jti") in _blacklist:
            return None
        return payload
    except Exception:
        return None


def blacklist_token(token: str) -> None:
    """Add a token's JTI to the blacklist (logout)."""
    payload = decode_token(token)
    if payload and "jti" in payload:
        _blacklist.add(payload["jti"])


def create_token_pair(username: str) -> Dict[str, str]:
    """Create both access and refresh tokens."""
    return {
        "access_token": create_token(username, "access"),
        "refresh_token": create_token(username, "refresh"),
        "token_type": "Bearer",
        "expires_in": _ACCESS_TTL,
    }


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, str]]:
    """
    Use a refresh token to get a new access token.
    The old refresh token is blacklisted (rotation).
    """
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return None
    blacklist_token(refresh_token)
    return create_token_pair(payload["sub"])


def get_username_from_token(token: str) -> Optional[str]:
    """Extract username from a valid access token."""
    payload = decode_token(token)
    if payload and payload.get("type") == "access":
        return payload.get("sub")
    return None
