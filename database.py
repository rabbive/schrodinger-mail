#!/usr/bin/env python3
"""
database.py — SQLite Persistence Layer
========================================
Provides persistent storage for users, emails, pending messages, contacts,
drafts, attachments, sessions, audit logs, and replay-detection IDs.

Thread-safe: all writes are serialised through a threading lock.
"""

from __future__ import annotations

import hashlib
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).parent / "quantum_email.db"

_conn: Optional[sqlite3.Connection] = None
_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables if they don't exist.  Safe to call multiple times."""
    try:
        conn = _get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                username       TEXT PRIMARY KEY,
                password_hash  TEXT,
                kyber_pk       BLOB NOT NULL,
                kyber_sk       BLOB NOT NULL,
                dilithium_pk   BLOB NOT NULL,
                dilithium_sk   BLOB NOT NULL,
                rsa_pk         BLOB,
                rsa_sk         BLOB,
                created_at     TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS emails (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient   TEXT NOT NULL,
                sender      TEXT NOT NULL,
                subject     TEXT DEFAULT '',
                plaintext   TEXT,
                verified    INTEGER NOT NULL DEFAULT 0,
                error       TEXT,
                read        INTEGER NOT NULL DEFAULT 0,
                folder      TEXT NOT NULL DEFAULT 'inbox',
                enc_subject INTEGER NOT NULL DEFAULT 0,
                timestamp   TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS pending (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient        TEXT NOT NULL,
                sender           TEXT NOT NULL,
                encapsulated_key BLOB NOT NULL,
                ciphertext       BLOB NOT NULL,
                nonce            BLOB NOT NULL,
                tag              BLOB NOT NULL
            );

            CREATE TABLE IF NOT EXISTS drafts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                owner       TEXT NOT NULL,
                recipient   TEXT DEFAULT '',
                subject     TEXT DEFAULT '',
                body        TEXT DEFAULT '',
                updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                owner                   TEXT NOT NULL,
                name                    TEXT NOT NULL,
                username                TEXT DEFAULT '',
                kyber_fingerprint       TEXT DEFAULT '',
                dilithium_fingerprint   TEXT DEFAULT '',
                verified                INTEGER NOT NULL DEFAULT 0,
                notes                   TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS attachments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id    INTEGER,
                filename    TEXT NOT NULL,
                mimetype    TEXT DEFAULT 'application/octet-stream',
                size_bytes  INTEGER NOT NULL DEFAULT 0,
                data        BLOB NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                username     TEXT NOT NULL,
                created_at   TEXT NOT NULL,
                last_active  TEXT NOT NULL,
                ip_address   TEXT DEFAULT '',
                user_agent   TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT NOT NULL,
                action      TEXT NOT NULL,
                details     TEXT DEFAULT '',
                ip_address  TEXT DEFAULT '',
                timestamp   TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS seen_ids (
                username    TEXT NOT NULL,
                message_id  TEXT NOT NULL,
                PRIMARY KEY (username, message_id)
            );

            CREATE TABLE IF NOT EXISTS user_settings (
                username    TEXT PRIMARY KEY,
                signature   TEXT DEFAULT '',
                theme       TEXT DEFAULT 'dark',
                shortcuts   INTEGER NOT NULL DEFAULT 1,
                notifications INTEGER NOT NULL DEFAULT 1
            );
        """)
        conn.commit()
        _migrate(conn)
    except Exception as exc:
        print(f"[DB] init_db error: {exc}")
        raise


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns that may be missing from older database versions."""
    try:
        existing = {
            row[1]
            for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        if "rsa_pk" not in existing:
            conn.execute("ALTER TABLE users ADD COLUMN rsa_pk BLOB")
            conn.execute("ALTER TABLE users ADD COLUMN rsa_sk BLOB")
            conn.commit()
            print("[DB] Migrated: added rsa_pk/rsa_sk columns to users table.")
    except Exception as exc:
        print(f"[DB] migration warning: {exc}")


# ── Users ────────────────────────────────────────────────────────────────────

def save_user(
    username: str,
    kyber_pk: bytes,
    kyber_sk: bytes,
    dilithium_pk: bytes,
    dilithium_sk: bytes,
    password_hash: Optional[str] = None,
    rsa_pk: Optional[bytes] = None,
    rsa_sk: Optional[bytes] = None,
) -> None:
    try:
        with _lock:
            conn = _get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO users "
                "(username, password_hash, kyber_pk, kyber_sk, dilithium_pk, dilithium_sk, rsa_pk, rsa_sk) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (username, password_hash, kyber_pk, kyber_sk, dilithium_pk, dilithium_sk, rsa_pk, rsa_sk),
            )
            conn.commit()
    except Exception as exc:
        print(f"[DB] save_user error: {exc}")


def load_users() -> List[Dict[str, Any]]:
    try:
        conn = _get_conn()
        rows = conn.execute("SELECT * FROM users").fetchall()
        result = []
        for r in rows:
            user = {
                "username": r["username"],
                "password_hash": r["password_hash"],
                "kyber_pk": bytes(r["kyber_pk"]),
                "kyber_sk": bytes(r["kyber_sk"]),
                "dilithium_pk": bytes(r["dilithium_pk"]),
                "dilithium_sk": bytes(r["dilithium_sk"]),
                "created_at": r["created_at"],
            }
            try:
                user["rsa_pk"] = bytes(r["rsa_pk"]) if r["rsa_pk"] else None
                user["rsa_sk"] = bytes(r["rsa_sk"]) if r["rsa_sk"] else None
            except (IndexError, KeyError):
                user["rsa_pk"] = None
                user["rsa_sk"] = None
            result.append(user)
        return result
    except Exception:
        return []


def user_exists(username: str) -> bool:
    conn = _get_conn()
    row = conn.execute(
        "SELECT 1 FROM users WHERE username = ?", (username,)
    ).fetchone()
    return row is not None


def get_password_hash(username: str) -> Optional[str]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    return row["password_hash"] if row else None


def update_password(username: str, password_hash: str) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (password_hash, username),
        )
        conn.commit()


# ── Emails ───────────────────────────────────────────────────────────────────

def save_email(
    recipient: str,
    sender: str,
    plaintext: Optional[str],
    verified: bool,
    error: Optional[str] = None,
    folder: str = "inbox",
    subject: str = "",
    enc_subject: bool = False,
) -> int:
    try:
        with _lock:
            conn = _get_conn()
            cur = conn.execute(
                "INSERT INTO emails "
                "(recipient, sender, subject, plaintext, verified, error, folder, enc_subject) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (recipient, sender, subject, plaintext, int(verified), error, folder, int(enc_subject)),
            )
            conn.commit()
            return cur.lastrowid  # type: ignore[return-value]
    except Exception as exc:
        print(f"[DB] save_email error: {exc}")
        return -1


def load_emails(recipient: str, folder: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = _get_conn()
    if folder:
        rows = conn.execute(
            "SELECT * FROM emails WHERE recipient = ? AND folder = ? ORDER BY id ASC",
            (recipient, folder),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM emails WHERE recipient = ? ORDER BY id ASC",
            (recipient,),
        ).fetchall()
    return [_email_row_to_dict(r) for r in rows]


def load_emails_by_folder(username: str, folder: str) -> List[Dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM emails WHERE recipient = ? AND folder = ? ORDER BY id ASC",
        (username, folder),
    ).fetchall()
    return [_email_row_to_dict(r) for r in rows]


def move_email(email_id: int, folder: str) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute("UPDATE emails SET folder = ? WHERE id = ?", (folder, email_id))
        conn.commit()


def delete_email_permanent(email_id: int) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM emails WHERE id = ?", (email_id,))
        conn.commit()


def empty_trash(username: str) -> int:
    with _lock:
        conn = _get_conn()
        cur = conn.execute(
            "DELETE FROM emails WHERE recipient = ? AND folder = 'trash'",
            (username,),
        )
        conn.commit()
        return cur.rowcount


def mark_read(email_id: int) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute("UPDATE emails SET read = 1 WHERE id = ?", (email_id,))
        conn.commit()


def search_emails(recipient: str, query: str) -> List[Dict[str, Any]]:
    conn = _get_conn()
    q = f"%{query}%"
    rows = conn.execute(
        "SELECT * FROM emails WHERE recipient = ? "
        "AND (sender LIKE ? OR subject LIKE ? OR plaintext LIKE ?) ORDER BY id ASC",
        (recipient, q, q, q),
    ).fetchall()
    return [_email_row_to_dict(r) for r in rows]


def get_folder_counts(username: str) -> Dict[str, Dict[str, int]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT folder, COUNT(*) as total, "
        "SUM(CASE WHEN read = 0 THEN 1 ELSE 0 END) as unread "
        "FROM emails WHERE recipient = ? GROUP BY folder",
        (username,),
    ).fetchall()
    counts: Dict[str, Dict[str, int]] = {}
    for r in rows:
        counts[r["folder"]] = {"total": r["total"], "unread": r["unread"]}
    return counts


def _email_row_to_dict(r: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": r["id"],
        "sender": r["sender"],
        "subject": r["subject"],
        "plaintext": r["plaintext"],
        "verified": bool(r["verified"]),
        "error": r["error"],
        "read": bool(r["read"]),
        "folder": r["folder"],
        "enc_subject": bool(r["enc_subject"]),
        "timestamp": r["timestamp"],
    }


# ── Pending ──────────────────────────────────────────────────────────────────

def save_pending(
    recipient: str, sender: str,
    encapsulated_key: bytes, ciphertext: bytes, nonce: bytes, tag: bytes,
) -> int:
    try:
        with _lock:
            conn = _get_conn()
            cur = conn.execute(
                "INSERT INTO pending "
                "(recipient, sender, encapsulated_key, ciphertext, nonce, tag) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (recipient, sender, encapsulated_key, ciphertext, nonce, tag),
            )
            conn.commit()
            return cur.lastrowid  # type: ignore[return-value]
    except Exception as exc:
        print(f"[DB] save_pending error: {exc}")
        return -1


def load_pending(recipient: str) -> List[Dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM pending WHERE recipient = ? ORDER BY id ASC",
        (recipient,),
    ).fetchall()
    return [
        {
            "id": r["id"], "sender": r["sender"],
            "encapsulated_key": bytes(r["encapsulated_key"]),
            "ciphertext": bytes(r["ciphertext"]),
            "nonce": bytes(r["nonce"]), "tag": bytes(r["tag"]),
        }
        for r in rows
    ]


def delete_pending(recipient: str) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM pending WHERE recipient = ?", (recipient,))
        conn.commit()


# ── Drafts ───────────────────────────────────────────────────────────────────

def save_draft(owner: str, recipient: str, subject: str, body: str, draft_id: Optional[int] = None) -> int:
    with _lock:
        conn = _get_conn()
        if draft_id:
            conn.execute(
                "UPDATE drafts SET recipient=?, subject=?, body=?, updated_at=? WHERE id=? AND owner=?",
                (recipient, subject, body, _now(), draft_id, owner),
            )
            conn.commit()
            return draft_id
        cur = conn.execute(
            "INSERT INTO drafts (owner, recipient, subject, body, updated_at) VALUES (?,?,?,?,?)",
            (owner, recipient, subject, body, _now()),
        )
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]


def load_drafts(owner: str) -> List[Dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM drafts WHERE owner = ? ORDER BY updated_at DESC", (owner,)
    ).fetchall()
    return [
        {"id": r["id"], "recipient": r["recipient"], "subject": r["subject"],
         "body": r["body"], "updated_at": r["updated_at"]}
        for r in rows
    ]


def delete_draft(draft_id: int, owner: str) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM drafts WHERE id = ? AND owner = ?", (draft_id, owner))
        conn.commit()


# ── Contacts ─────────────────────────────────────────────────────────────────

def save_contact(owner: str, name: str, username: str = "", notes: str = "",
                 kyber_fp: str = "", dilithium_fp: str = "", verified: bool = False) -> int:
    with _lock:
        conn = _get_conn()
        cur = conn.execute(
            "INSERT INTO contacts (owner, name, username, kyber_fingerprint, "
            "dilithium_fingerprint, verified, notes) VALUES (?,?,?,?,?,?,?)",
            (owner, name, username, kyber_fp, dilithium_fp, int(verified), notes),
        )
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]


def load_contacts(owner: str) -> List[Dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM contacts WHERE owner = ? ORDER BY name ASC", (owner,)
    ).fetchall()
    return [
        {"id": r["id"], "name": r["name"], "username": r["username"],
         "kyber_fingerprint": r["kyber_fingerprint"],
         "dilithium_fingerprint": r["dilithium_fingerprint"],
         "verified": bool(r["verified"]), "notes": r["notes"]}
        for r in rows
    ]


def delete_contact(contact_id: int, owner: str) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM contacts WHERE id = ? AND owner = ?", (contact_id, owner))
        conn.commit()


def update_contact_verified(contact_id: int, verified: bool) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute("UPDATE contacts SET verified = ? WHERE id = ?", (int(verified), contact_id))
        conn.commit()


# ── Attachments ──────────────────────────────────────────────────────────────

def save_attachment(email_id: int, filename: str, mimetype: str, data: bytes) -> int:
    with _lock:
        conn = _get_conn()
        cur = conn.execute(
            "INSERT INTO attachments (email_id, filename, mimetype, size_bytes, data) "
            "VALUES (?,?,?,?,?)",
            (email_id, filename, mimetype, len(data), data),
        )
        conn.commit()
        return cur.lastrowid  # type: ignore[return-value]


def load_attachments(email_id: int) -> List[Dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, email_id, filename, mimetype, size_bytes FROM attachments WHERE email_id = ?",
        (email_id,),
    ).fetchall()
    return [
        {"id": r["id"], "filename": r["filename"], "mimetype": r["mimetype"],
         "size_bytes": r["size_bytes"]}
        for r in rows
    ]


def get_attachment_data(attachment_id: int) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,)).fetchone()
    if not row:
        return None
    return {"id": row["id"], "filename": row["filename"], "mimetype": row["mimetype"],
            "data": bytes(row["data"]), "size_bytes": row["size_bytes"]}


# ── Sessions ─────────────────────────────────────────────────────────────────

def save_session(session_id: str, username: str, ip: str = "", ua: str = "") -> None:
    with _lock:
        conn = _get_conn()
        now = _now()
        conn.execute(
            "INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?,?)",
            (session_id, username, now, now, ip, ua),
        )
        conn.commit()


def touch_session(session_id: str) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute(
            "UPDATE sessions SET last_active = ? WHERE session_id = ?",
            (_now(), session_id),
        )
        conn.commit()


def load_sessions(username: str) -> List[Dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM sessions WHERE username = ? ORDER BY last_active DESC",
        (username,),
    ).fetchall()
    return [
        {"session_id": r["session_id"], "username": r["username"],
         "created_at": r["created_at"], "last_active": r["last_active"],
         "ip_address": r["ip_address"], "user_agent": r["user_agent"]}
        for r in rows
    ]


def delete_session(session_id: str) -> None:
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()


def session_exists(session_id: str) -> Optional[str]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT username FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    return row["username"] if row else None


# ── Audit Log ────────────────────────────────────────────────────────────────

def log_audit(username: str, action: str, details: str = "", ip: str = "") -> None:
    try:
        with _lock:
            conn = _get_conn()
            conn.execute(
                "INSERT INTO audit_log (username, action, details, ip_address) "
                "VALUES (?,?,?,?)",
                (username, action, details, ip),
            )
            conn.commit()
    except Exception:
        pass


def load_audit_log(username: str, limit: int = 100) -> List[Dict[str, Any]]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM audit_log WHERE username = ? ORDER BY id DESC LIMIT ?",
        (username, limit),
    ).fetchall()
    return [
        {"id": r["id"], "action": r["action"], "details": r["details"],
         "ip_address": r["ip_address"], "timestamp": r["timestamp"]}
        for r in rows
    ]


# ── Seen Message IDs (Replay Protection) ─────────────────────────────────────

def save_seen_id(username: str, message_id: str) -> None:
    try:
        with _lock:
            conn = _get_conn()
            conn.execute(
                "INSERT OR IGNORE INTO seen_ids VALUES (?,?)",
                (username, message_id),
            )
            conn.commit()
    except Exception:
        pass


def load_seen_ids(username: str) -> set:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT message_id FROM seen_ids WHERE username = ?", (username,)
    ).fetchall()
    return {r["message_id"] for r in rows}


# ── User Settings ────────────────────────────────────────────────────────────

def get_settings(username: str) -> Dict[str, Any]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM user_settings WHERE username = ?", (username,)
    ).fetchone()
    if row:
        return {"signature": row["signature"], "theme": row["theme"],
                "shortcuts": bool(row["shortcuts"]),
                "notifications": bool(row["notifications"])}
    return {"signature": "", "theme": "dark", "shortcuts": True, "notifications": True}


def save_settings(username: str, **kwargs: Any) -> None:
    with _lock:
        conn = _get_conn()
        existing = conn.execute(
            "SELECT 1 FROM user_settings WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            parts = []
            vals = []
            for k, v in kwargs.items():
                if k in ("signature", "theme", "shortcuts", "notifications"):
                    parts.append(f"{k} = ?")
                    vals.append(int(v) if isinstance(v, bool) else v)
            if parts:
                vals.append(username)
                conn.execute(
                    f"UPDATE user_settings SET {', '.join(parts)} WHERE username = ?",
                    vals,
                )
        else:
            sig = kwargs.get("signature", "")
            theme = kwargs.get("theme", "dark")
            sc = int(kwargs.get("shortcuts", True))
            notif = int(kwargs.get("notifications", True))
            conn.execute(
                "INSERT INTO user_settings VALUES (?,?,?,?,?)",
                (username, sig, theme, sc, notif),
            )
        conn.commit()
