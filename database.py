#!/usr/bin/env python3
"""
database.py — Persistence Layer (SQLAlchemy)
=============================================
Provides persistent storage for users, emails, pending messages, contacts,
drafts, attachments, sessions, audit logs, replay-detection IDs, and
ratchet states.

Supports both SQLite (development) and PostgreSQL (production) via
SQLAlchemy ORM.  All public function signatures are backward-compatible
with the original raw-SQLite implementation.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

import config
from models import (
    Attachment, AuditLog, Base, Contact, Draft, Email, Pending,
    RatchetState, SeenId, SessionRecord, User, UserSettings,
    create_all, get_engine, get_session_factory,
)

# Re-export for backward compatibility
DB_PATH = config.DB_PATH

_engine = None
_SessionFactory = None
_lock = threading.Lock()


def _get_session() -> Session:
    global _engine, _SessionFactory
    if _engine is None:
        _engine = get_engine()
        _SessionFactory = get_session_factory(_engine)
    return _SessionFactory()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_str() -> str:
    return _now().isoformat()


# ── Schema ────────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables.  Safe to call multiple times."""
    global _engine, _SessionFactory
    _engine = get_engine()
    _SessionFactory = get_session_factory(_engine)
    create_all(_engine)


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
    encrypted_key_blob: Optional[bytes] = None,
) -> None:
    try:
        with _lock:
            s = _get_session()
            try:
                existing = s.get(User, username)
                if existing:
                    existing.kyber_pk = kyber_pk
                    existing.kyber_sk = kyber_sk
                    existing.dilithium_pk = dilithium_pk
                    existing.dilithium_sk = dilithium_sk
                    if password_hash is not None:
                        existing.password_hash = password_hash
                    if rsa_pk is not None:
                        existing.rsa_pk = rsa_pk
                    if rsa_sk is not None:
                        existing.rsa_sk = rsa_sk
                    if encrypted_key_blob is not None:
                        existing.encrypted_key_blob = encrypted_key_blob
                else:
                    user = User(
                        username=username, password_hash=password_hash,
                        kyber_pk=kyber_pk, kyber_sk=kyber_sk,
                        dilithium_pk=dilithium_pk, dilithium_sk=dilithium_sk,
                        rsa_pk=rsa_pk, rsa_sk=rsa_sk,
                        encrypted_key_blob=encrypted_key_blob,
                    )
                    s.add(user)
                s.commit()
            finally:
                s.close()
    except Exception as exc:
        print(f"[DB] save_user error: {exc}")


def load_users() -> List[Dict[str, Any]]:
    try:
        s = _get_session()
        try:
            users = s.query(User).all()
            return [
                {
                    "username": u.username,
                    "password_hash": u.password_hash,
                    "kyber_pk": bytes(u.kyber_pk),
                    "kyber_sk": bytes(u.kyber_sk),
                    "dilithium_pk": bytes(u.dilithium_pk),
                    "dilithium_sk": bytes(u.dilithium_sk),
                    "rsa_pk": bytes(u.rsa_pk) if u.rsa_pk else None,
                    "rsa_sk": bytes(u.rsa_sk) if u.rsa_sk else None,
                    "encrypted_key_blob": bytes(u.encrypted_key_blob) if u.encrypted_key_blob else None,
                    "created_at": str(u.created_at) if u.created_at else "",
                }
                for u in users
            ]
        finally:
            s.close()
    except Exception:
        return []


def user_exists(username: str) -> bool:
    s = _get_session()
    try:
        return s.get(User, username) is not None
    finally:
        s.close()


def get_password_hash(username: str) -> Optional[str]:
    s = _get_session()
    try:
        user = s.get(User, username)
        return user.password_hash if user else None
    finally:
        s.close()


def update_password(username: str, password_hash: str) -> None:
    with _lock:
        s = _get_session()
        try:
            user = s.get(User, username)
            if user:
                user.password_hash = password_hash
                s.commit()
        finally:
            s.close()


def get_encrypted_key_blob(username: str) -> Optional[bytes]:
    s = _get_session()
    try:
        user = s.get(User, username)
        return bytes(user.encrypted_key_blob) if user and user.encrypted_key_blob else None
    finally:
        s.close()


def save_encrypted_key_blob(username: str, blob: bytes) -> None:
    with _lock:
        s = _get_session()
        try:
            user = s.get(User, username)
            if user:
                user.encrypted_key_blob = blob
                s.commit()
        finally:
            s.close()


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
    thread_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
) -> int:
    try:
        with _lock:
            s = _get_session()
            try:
                email = Email(
                    recipient=recipient, sender=sender, subject=subject,
                    plaintext=plaintext, verified=verified, error=error,
                    folder=folder, enc_subject=enc_subject,
                    thread_id=thread_id, in_reply_to=in_reply_to,
                )
                s.add(email)
                s.commit()
                return email.id
            finally:
                s.close()
    except Exception as exc:
        print(f"[DB] save_email error: {exc}")
        return -1


def load_emails(recipient: str, folder: Optional[str] = None) -> List[Dict[str, Any]]:
    s = _get_session()
    try:
        q = s.query(Email).filter(Email.recipient == recipient)
        if folder:
            q = q.filter(Email.folder == folder)
        rows = q.order_by(Email.id.asc()).all()
        return [_email_to_dict(r) for r in rows]
    finally:
        s.close()


def load_emails_by_folder(username: str, folder: str) -> List[Dict[str, Any]]:
    s = _get_session()
    try:
        rows = (
            s.query(Email)
            .filter(Email.recipient == username, Email.folder == folder)
            .order_by(Email.id.asc())
            .all()
        )
        return [_email_to_dict(r) for r in rows]
    finally:
        s.close()


def load_thread(thread_id: str) -> List[Dict[str, Any]]:
    """Load all emails in a conversation thread."""
    s = _get_session()
    try:
        rows = (
            s.query(Email)
            .filter(Email.thread_id == thread_id)
            .order_by(Email.id.asc())
            .all()
        )
        return [_email_to_dict(r) for r in rows]
    finally:
        s.close()


def move_email(email_id: int, folder: str) -> None:
    with _lock:
        s = _get_session()
        try:
            email = s.get(Email, email_id)
            if email:
                email.folder = folder
                s.commit()
        finally:
            s.close()


def delete_email_permanent(email_id: int) -> None:
    with _lock:
        s = _get_session()
        try:
            email = s.get(Email, email_id)
            if email:
                s.delete(email)
                s.commit()
        finally:
            s.close()


def empty_trash(username: str) -> int:
    with _lock:
        s = _get_session()
        try:
            count = (
                s.query(Email)
                .filter(Email.recipient == username, Email.folder == "trash")
                .delete()
            )
            s.commit()
            return count
        finally:
            s.close()


def mark_read(email_id: int) -> None:
    with _lock:
        s = _get_session()
        try:
            email = s.get(Email, email_id)
            if email:
                email.read = True
                s.commit()
        finally:
            s.close()


def search_emails(recipient: str, query: str) -> List[Dict[str, Any]]:
    s = _get_session()
    try:
        q_like = f"%{query}%"
        rows = (
            s.query(Email)
            .filter(
                Email.recipient == recipient,
                (Email.sender.like(q_like))
                | (Email.subject.like(q_like))
                | (Email.plaintext.like(q_like)),
            )
            .order_by(Email.id.asc())
            .all()
        )
        return [_email_to_dict(r) for r in rows]
    finally:
        s.close()


def get_folder_counts(username: str) -> Dict[str, Dict[str, int]]:
    s = _get_session()
    try:
        from sqlalchemy import case, func
        rows = (
            s.query(
                Email.folder,
                func.count(Email.id).label("total"),
                func.sum(case((Email.read == False, 1), else_=0)).label("unread"),  # noqa: E712
            )
            .filter(Email.recipient == username)
            .group_by(Email.folder)
            .all()
        )
        return {r.folder: {"total": r.total, "unread": int(r.unread or 0)} for r in rows}
    finally:
        s.close()


def _email_to_dict(r: Email) -> Dict[str, Any]:
    return {
        "id": r.id,
        "sender": r.sender,
        "subject": r.subject,
        "plaintext": r.plaintext,
        "verified": bool(r.verified),
        "error": r.error,
        "read": bool(r.read),
        "folder": r.folder,
        "enc_subject": bool(r.enc_subject),
        "thread_id": r.thread_id,
        "in_reply_to": r.in_reply_to,
        "timestamp": str(r.timestamp) if r.timestamp else "",
    }


# ── Pending ──────────────────────────────────────────────────────────────────

def save_pending(
    recipient: str, sender: str,
    encapsulated_key: bytes, ciphertext: bytes, nonce: bytes, tag: bytes,
) -> int:
    try:
        with _lock:
            s = _get_session()
            try:
                p = Pending(
                    recipient=recipient, sender=sender,
                    encapsulated_key=encapsulated_key, ciphertext=ciphertext,
                    nonce=nonce, tag=tag,
                )
                s.add(p)
                s.commit()
                return p.id
            finally:
                s.close()
    except Exception as exc:
        print(f"[DB] save_pending error: {exc}")
        return -1


def load_pending(recipient: str) -> List[Dict[str, Any]]:
    s = _get_session()
    try:
        rows = (
            s.query(Pending)
            .filter(Pending.recipient == recipient)
            .order_by(Pending.id.asc())
            .all()
        )
        return [
            {
                "id": r.id, "sender": r.sender,
                "encapsulated_key": bytes(r.encapsulated_key),
                "ciphertext": bytes(r.ciphertext),
                "nonce": bytes(r.nonce), "tag": bytes(r.tag),
            }
            for r in rows
        ]
    finally:
        s.close()


def delete_pending(recipient: str) -> None:
    with _lock:
        s = _get_session()
        try:
            s.query(Pending).filter(Pending.recipient == recipient).delete()
            s.commit()
        finally:
            s.close()


# ── Drafts ───────────────────────────────────────────────────────────────────

def save_draft(
    owner: str, recipient: str, subject: str, body: str,
    draft_id: Optional[int] = None,
) -> int:
    with _lock:
        s = _get_session()
        try:
            if draft_id:
                draft = s.get(Draft, draft_id)
                if draft and draft.owner == owner:
                    draft.recipient = recipient
                    draft.subject = subject
                    draft.body = body
                    draft.updated_at = _now()
                    s.commit()
                    return draft_id
            d = Draft(
                owner=owner, recipient=recipient,
                subject=subject, body=body, updated_at=_now(),
            )
            s.add(d)
            s.commit()
            return d.id
        finally:
            s.close()


def load_drafts(owner: str) -> List[Dict[str, Any]]:
    s = _get_session()
    try:
        rows = (
            s.query(Draft)
            .filter(Draft.owner == owner)
            .order_by(Draft.updated_at.desc())
            .all()
        )
        return [
            {
                "id": r.id, "recipient": r.recipient, "subject": r.subject,
                "body": r.body, "updated_at": str(r.updated_at),
            }
            for r in rows
        ]
    finally:
        s.close()


def delete_draft(draft_id: int, owner: str) -> None:
    with _lock:
        s = _get_session()
        try:
            draft = s.get(Draft, draft_id)
            if draft and draft.owner == owner:
                s.delete(draft)
                s.commit()
        finally:
            s.close()


# ── Contacts ─────────────────────────────────────────────────────────────────

def save_contact(
    owner: str, name: str, username: str = "", notes: str = "",
    kyber_fp: str = "", dilithium_fp: str = "", verified: bool = False,
) -> int:
    with _lock:
        s = _get_session()
        try:
            c = Contact(
                owner=owner, name=name, username=username,
                kyber_fingerprint=kyber_fp, dilithium_fingerprint=dilithium_fp,
                verified=verified, notes=notes,
            )
            s.add(c)
            s.commit()
            return c.id
        finally:
            s.close()


def load_contacts(owner: str) -> List[Dict[str, Any]]:
    s = _get_session()
    try:
        rows = (
            s.query(Contact)
            .filter(Contact.owner == owner)
            .order_by(Contact.name.asc())
            .all()
        )
        return [
            {
                "id": r.id, "name": r.name, "username": r.username,
                "kyber_fingerprint": r.kyber_fingerprint,
                "dilithium_fingerprint": r.dilithium_fingerprint,
                "verified": bool(r.verified), "notes": r.notes,
            }
            for r in rows
        ]
    finally:
        s.close()


def delete_contact(contact_id: int, owner: str) -> None:
    with _lock:
        s = _get_session()
        try:
            c = s.get(Contact, contact_id)
            if c and c.owner == owner:
                s.delete(c)
                s.commit()
        finally:
            s.close()


def update_contact_verified(contact_id: int, verified: bool) -> None:
    with _lock:
        s = _get_session()
        try:
            c = s.get(Contact, contact_id)
            if c:
                c.verified = verified
                s.commit()
        finally:
            s.close()


# ── Attachments ──────────────────────────────────────────────────────────────

def save_attachment(
    email_id: int, filename: str, mimetype: str, data: bytes,
    encryption_key: Optional[bytes] = None,
) -> int:
    with _lock:
        s = _get_session()
        try:
            a = Attachment(
                email_id=email_id, filename=filename, mimetype=mimetype,
                size_bytes=len(data), data=data, encryption_key=encryption_key,
            )
            s.add(a)
            s.commit()
            return a.id
        finally:
            s.close()


def load_attachments(email_id: int) -> List[Dict[str, Any]]:
    s = _get_session()
    try:
        rows = (
            s.query(Attachment)
            .filter(Attachment.email_id == email_id)
            .all()
        )
        return [
            {
                "id": r.id, "filename": r.filename, "mimetype": r.mimetype,
                "size_bytes": r.size_bytes,
                "encrypted": r.encryption_key is not None,
            }
            for r in rows
        ]
    finally:
        s.close()


def get_attachment_data(attachment_id: int) -> Optional[Dict[str, Any]]:
    s = _get_session()
    try:
        r = s.get(Attachment, attachment_id)
        if not r:
            return None
        return {
            "id": r.id, "filename": r.filename, "mimetype": r.mimetype,
            "data": bytes(r.data), "size_bytes": r.size_bytes,
            "encryption_key": bytes(r.encryption_key) if r.encryption_key else None,
        }
    finally:
        s.close()


# ── Sessions ─────────────────────────────────────────────────────────────────

def save_session(session_id: str, username: str, ip: str = "", ua: str = "") -> None:
    with _lock:
        s = _get_session()
        try:
            now = _now()
            existing = s.get(SessionRecord, session_id)
            if existing:
                existing.last_active = now
                existing.ip_address = ip
                existing.user_agent = ua
            else:
                rec = SessionRecord(
                    session_id=session_id, username=username,
                    created_at=now, last_active=now,
                    ip_address=ip, user_agent=ua,
                )
                s.add(rec)
            s.commit()
        finally:
            s.close()


def touch_session(session_id: str) -> None:
    with _lock:
        s = _get_session()
        try:
            rec = s.get(SessionRecord, session_id)
            if rec:
                rec.last_active = _now()
                s.commit()
        finally:
            s.close()


def load_sessions(username: str) -> List[Dict[str, Any]]:
    s = _get_session()
    try:
        rows = (
            s.query(SessionRecord)
            .filter(SessionRecord.username == username)
            .order_by(SessionRecord.last_active.desc())
            .all()
        )
        return [
            {
                "session_id": r.session_id, "username": r.username,
                "created_at": str(r.created_at), "last_active": str(r.last_active),
                "ip_address": r.ip_address, "user_agent": r.user_agent,
            }
            for r in rows
        ]
    finally:
        s.close()


def delete_session(session_id: str) -> None:
    with _lock:
        s = _get_session()
        try:
            rec = s.get(SessionRecord, session_id)
            if rec:
                s.delete(rec)
                s.commit()
        finally:
            s.close()


def session_exists(session_id: str) -> Optional[str]:
    s = _get_session()
    try:
        rec = s.get(SessionRecord, session_id)
        return rec.username if rec else None
    finally:
        s.close()


# ── Audit Log ────────────────────────────────────────────────────────────────

def log_audit(username: str, action: str, details: str = "", ip: str = "") -> None:
    try:
        with _lock:
            s = _get_session()
            try:
                entry = AuditLog(
                    username=username, action=action,
                    details=details, ip_address=ip,
                )
                s.add(entry)
                s.commit()
            finally:
                s.close()
    except Exception:
        pass


def load_audit_log(username: str, limit: int = 100) -> List[Dict[str, Any]]:
    s = _get_session()
    try:
        rows = (
            s.query(AuditLog)
            .filter(AuditLog.username == username)
            .order_by(AuditLog.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id, "action": r.action, "details": r.details,
                "ip_address": r.ip_address, "timestamp": str(r.timestamp),
            }
            for r in rows
        ]
    finally:
        s.close()


# ── Seen Message IDs (Replay Protection) ─────────────────────────────────────

def save_seen_id(username: str, message_id: str) -> None:
    try:
        with _lock:
            s = _get_session()
            try:
                existing = s.get(SeenId, (username, message_id))
                if not existing:
                    s.add(SeenId(username=username, message_id=message_id))
                    s.commit()
            finally:
                s.close()
    except Exception:
        pass


def load_seen_ids(username: str) -> Set[str]:
    s = _get_session()
    try:
        rows = s.query(SeenId).filter(SeenId.username == username).all()
        return {r.message_id for r in rows}
    finally:
        s.close()


# ── User Settings ────────────────────────────────────────────────────────────

def get_settings(username: str) -> Dict[str, Any]:
    s = _get_session()
    try:
        row = s.get(UserSettings, username)
        if row:
            return {
                "signature": row.signature, "theme": row.theme,
                "shortcuts": bool(row.shortcuts),
                "notifications": bool(row.notifications),
            }
        return {"signature": "", "theme": "dark", "shortcuts": True, "notifications": True}
    finally:
        s.close()


def save_settings(username: str, **kwargs: Any) -> None:
    with _lock:
        s = _get_session()
        try:
            row = s.get(UserSettings, username)
            if row:
                for k, v in kwargs.items():
                    if hasattr(row, k):
                        setattr(row, k, v)
            else:
                row = UserSettings(
                    username=username,
                    signature=kwargs.get("signature", ""),
                    theme=kwargs.get("theme", "dark"),
                    shortcuts=kwargs.get("shortcuts", True),
                    notifications=kwargs.get("notifications", True),
                )
                s.add(row)
            s.commit()
        finally:
            s.close()


# ── Ratchet States (Forward Secrecy) ─────────────────────────────────────────

def save_ratchet_state(
    user_a: str, user_b: str, chain_key: bytes, step: int,
) -> None:
    with _lock:
        s = _get_session()
        try:
            existing = (
                s.query(RatchetState)
                .filter(RatchetState.user_a == user_a, RatchetState.user_b == user_b)
                .first()
            )
            if existing:
                existing.chain_key = chain_key
                existing.step = step
                existing.updated_at = _now()
            else:
                s.add(RatchetState(
                    user_a=user_a, user_b=user_b,
                    chain_key=chain_key, step=step,
                ))
            s.commit()
        finally:
            s.close()


def load_ratchet_state(user_a: str, user_b: str) -> Optional[Dict[str, Any]]:
    s = _get_session()
    try:
        r = (
            s.query(RatchetState)
            .filter(RatchetState.user_a == user_a, RatchetState.user_b == user_b)
            .first()
        )
        if not r:
            return None
        return {
            "chain_key": bytes(r.chain_key),
            "step": r.step,
        }
    finally:
        s.close()
