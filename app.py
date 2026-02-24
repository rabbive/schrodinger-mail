#!/usr/bin/env python3
"""
app.py — Flask Web Server for Schrödinger Mail
===========================================================
Full-featured email client with authentication, folder management, contacts,
drafts, attachments, audit logging, rate limiting, CSRF protection, and
comprehensive security showcase panels.
"""

from __future__ import annotations

import base64
import hashlib
import io
import os
import secrets
import uuid
from functools import wraps
from typing import Any, Dict, List, Optional

from flask import (Flask, Response, jsonify, redirect, render_template,
                   request, send_file, session, url_for)

import config
import crypto_utils
import database as db
from client import Client
from server import Server

# ── Flask app ────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = config.MAX_ATTACHMENT_BYTES + 1024 * 1024

# Rate limiting (graceful if redis not available)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(get_remote_address, app=app, default_limits=["200/minute"],
                      storage_uri="memory://")
except Exception:
    limiter = None

# ── Global state ─────────────────────────────────────────────────────────────

mail_server = Server()
clients: Dict[str, Client] = {}
inboxes: Dict[str, list] = {}

# Pending undo-send queue: {pending_id: {timer, data}}
undo_queue: Dict[str, Dict] = {}


# ── Bootstrap ────────────────────────────────────────────────────────────────

def _bootstrap() -> None:
    db.init_db()
    saved_users = db.load_users()
    if saved_users:
        for u in saved_users:
            seen_ids = db.load_seen_ids(u["username"])
            c = Client.from_keys(
                username=u["username"], server=mail_server,
                kyber_pk=u["kyber_pk"], kyber_sk=u["kyber_sk"],
                dilithium_pk=u["dilithium_pk"], dilithium_sk=u["dilithium_sk"],
                seen_ids=seen_ids,
                rsa_pk=u.get("rsa_pk"), rsa_sk=u.get("rsa_sk"),
            )
            clients[u["username"]] = c
            inboxes[u["username"]] = db.load_emails(u["username"])
    else:
        for name in ("alice", "bob"):
            c = Client(name, mail_server)
            clients[name] = c
            inboxes[name] = []
            db.save_user(name, c.kyber_pk, c.kyber_sk, c.dilithium_pk, c.dilithium_sk,
                         rsa_pk=c.rsa_pk, rsa_sk=c.rsa_sk)

_bootstrap()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _bytes_to_b64(obj: Any) -> Any:
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode("ascii")
    if isinstance(obj, dict):
        return {k: _bytes_to_b64(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_bytes_to_b64(item) for item in obj]
    return obj


def _user_info(name: str) -> Dict[str, Any]:
    c = clients[name]
    pending = len(mail_server.mailboxes.get(name, []))
    user_emails = inboxes.get(name, [])
    unread = sum(1 for e in user_emails if not e.get("read"))
    return {
        "username": name,
        "kyber_pk_bytes": len(c.kyber_pk),
        "kyber_sk_bytes": len(c.kyber_sk),
        "dilithium_pk_bytes": len(c.dilithium_pk),
        "dilithium_sk_bytes": len(c.dilithium_sk),
        "rsa_pk_bytes": len(c.rsa_pk) if c.rsa_pk else 0,
        "kyber_pk_preview": c.kyber_pk[:8].hex() + "...",
        "dilithium_pk_preview": c.dilithium_pk[:8].hex() + "...",
        "kyber_fingerprint": crypto_utils.key_fingerprint(c.kyber_pk),
        "dilithium_fingerprint": crypto_utils.key_fingerprint(c.dilithium_pk),
        "kyber_fingerprint_short": crypto_utils.key_fingerprint_short(c.kyber_pk),
        "dilithium_fingerprint_short": crypto_utils.key_fingerprint_short(c.dilithium_pk),
        "pending_messages": pending,
        "inbox_count": len(user_emails),
        "unread_count": unread,
        "has_password": db.get_password_hash(name) is not None,
        "has_rsa_keys": bool(c.rsa_pk),
    }


def _extract_subject(plaintext: Optional[str]) -> str:
    if not plaintext:
        return ""
    for line in plaintext.split("\n"):
        if line.startswith("Subject: "):
            return line[9:]
        if line == "":
            break
    return ""


def _validate_input(data: dict, *fields: str) -> Optional[str]:
    for f in fields:
        val = data.get(f, "")
        if isinstance(val, str):
            val = val.strip()
        if not val:
            return f"{f} is required."
    return None


def _get_ip() -> str:
    return request.remote_addr or ""


def _current_user() -> Optional[str]:
    return session.get("username")


def _require_auth(f):
    """Decorator: require login. If no passwords set at all, allow anonymous."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        has_any_password = any(db.get_password_hash(u) for u in clients)
        if has_any_password and not session.get("username"):
            return jsonify({"error": "Authentication required.", "login_required": True}), 401
        return f(*args, **kwargs)
    return wrapper


# ── CSRF Token ───────────────────────────────────────────────────────────────

@app.before_request
def _ensure_csrf():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)


@app.context_processor
def _inject_csrf():
    return {"csrf_token": session.get("csrf_token", "")}


def _check_csrf():
    token = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token") or ""
    if token != session.get("csrf_token", ""):
        return False
    return True


# ── Routes: Pages ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login")
def login_page():
    return render_template("index.html")


# ── Routes: Auth ─────────────────────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True)
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    if username not in clients:
        return jsonify({"error": "Unknown user."}), 404

    stored_hash = db.get_password_hash(username)
    if stored_hash:
        try:
            from argon2 import PasswordHasher
            ph = PasswordHasher()
            ph.verify(stored_hash, password)
        except Exception:
            db.log_audit(username, "login_failed", "Wrong password", _get_ip())
            return jsonify({"error": "Invalid password."}), 401
    # If no password set, allow login (demo mode)

    session["username"] = username
    sid = secrets.token_hex(16)
    session["session_id"] = sid
    db.save_session(sid, username, _get_ip(), request.user_agent.string)
    db.log_audit(username, "login", "Logged in", _get_ip())

    return jsonify({"ok": True, "user": _user_info(username)})


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    username = session.get("username", "")
    sid = session.get("session_id", "")
    if sid:
        db.delete_session(sid)
    if username:
        db.log_audit(username, "logout", "Logged out", _get_ip())
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/auth/set-password", methods=["POST"])
def api_set_password():
    data = request.get_json(force=True)
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    if username not in clients:
        return jsonify({"error": "Unknown user."}), 404
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters."}), 400

    from argon2 import PasswordHasher
    ph = PasswordHasher()
    hashed = ph.hash(password)
    db.update_password(username, hashed)
    db.log_audit(username, "password_set", "Password created/changed", _get_ip())

    return jsonify({"ok": True})


@app.route("/api/auth/status")
def api_auth_status():
    has_any_password = any(db.get_password_hash(u) for u in clients)
    return jsonify({
        "auth_enabled": has_any_password,
        "logged_in": "username" in session,
        "username": session.get("username", ""),
        "csrf_token": session.get("csrf_token", ""),
    })


# ── Routes: State ────────────────────────────────────────────────────────────

@app.route("/api/state")
def api_state():
    return jsonify({
        "kem_algorithm": crypto_utils.KEM_ALG,
        "sig_algorithm": crypto_utils.SIG_ALG,
        "dem_algorithm": "AES-256-GCM",
        "users": {name: _user_info(name) for name in clients},
    })


@app.route("/api/inbox/<username>")
def api_inbox(username: str):
    if username not in clients:
        return jsonify({"error": f"Unknown user '{username}'"}), 404
    return jsonify({"emails": inboxes.get(username, [])})


# ── Routes: Folders ──────────────────────────────────────────────────────────

@app.route("/api/folders/<username>")
def api_folders(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    counts = db.get_folder_counts(username)
    folders = ["inbox", "sent", "drafts", "archive", "trash"]
    result = []
    for f in folders:
        c = counts.get(f, {"total": 0, "unread": 0})
        if f == "drafts":
            drafts = db.load_drafts(username)
            result.append({"name": f, "total": len(drafts), "unread": len(drafts)})
        else:
            result.append({"name": f, "total": c["total"], "unread": c["unread"]})
    return jsonify({"folders": result})


@app.route("/api/emails/<username>/<folder>")
def api_emails_by_folder(username: str, folder: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    emails = db.load_emails_by_folder(username, folder)
    return jsonify({"emails": emails})


@app.route("/api/move/<username>/<int:email_id>", methods=["POST"])
def api_move_email(username: str, email_id: int):
    data = request.get_json(force=True)
    folder = data.get("folder", "").strip()
    if folder not in ("inbox", "sent", "archive", "trash"):
        return jsonify({"error": "Invalid folder."}), 400
    db.move_email(email_id, folder)
    _refresh_inbox(username)
    db.log_audit(username, "move_email", f"Moved email {email_id} to {folder}", _get_ip())
    return jsonify({"ok": True})


@app.route("/api/delete/<username>/<int:email_id>", methods=["POST"])
def api_delete_email(username: str, email_id: int):
    db.move_email(email_id, "trash")
    _refresh_inbox(username)
    return jsonify({"ok": True})


@app.route("/api/delete-permanent/<username>/<int:email_id>", methods=["DELETE"])
def api_delete_permanent(username: str, email_id: int):
    db.delete_email_permanent(email_id)
    _refresh_inbox(username)
    return jsonify({"ok": True})


@app.route("/api/empty-trash/<username>", methods=["DELETE"])
def api_empty_trash(username: str):
    count = db.empty_trash(username)
    _refresh_inbox(username)
    db.log_audit(username, "empty_trash", f"Permanently deleted {count} emails", _get_ip())
    return jsonify({"ok": True, "deleted": count})


def _refresh_inbox(username: str) -> None:
    inboxes[username] = db.load_emails(username)


# ── Routes: Send ─────────────────────────────────────────────────────────────

@app.route("/api/send", methods=["POST"])
def api_send():
    data = request.get_json(force=True)
    sender_name = data.get("sender", "").strip().lower()
    recipient_name = data.get("recipient", "").strip().lower()
    subject = data.get("subject", "").strip()[:config.MAX_SUBJECT_LEN]
    body = data.get("body", "").strip()[:config.MAX_BODY_LEN]
    encrypt_subject = data.get("encrypt_subject", False)
    security_level = data.get("security_level", 2)

    if sender_name not in clients:
        return jsonify({"error": f"Unknown sender '{sender_name}'"}), 404
    if recipient_name not in clients:
        return jsonify({"error": f"Unknown recipient '{recipient_name}'"}), 404
    if not subject or not body:
        return jsonify({"error": "Subject and body are required."}), 400

    client = clients[sender_name]

    sig = db.get_settings(sender_name).get("signature", "")
    if sig:
        body = body + "\n\n-- \n" + sig

    if security_level == 3:
        recipient_rsa_pk = clients[recipient_name].rsa_pk
        result = client.send_email_hybrid_with_log(
            recipient_name, subject, body, recipient_rsa_pk, encrypt_subject
        )
    else:
        result = client.send_email_with_log(recipient_name, subject, body, encrypt_subject)

    pkg = result["package"]
    db.save_pending(
        recipient=recipient_name, sender=sender_name,
        encapsulated_key=pkg["encapsulated_key"], ciphertext=pkg["ciphertext"],
        nonce=pkg["nonce"], tag=pkg["tag"],
    )

    sent_subject = subject if not encrypt_subject else result.get("subject", subject)
    level_label = {1: "Password", 2: "PQC", 3: "Hybrid RSA+Kyber"}.get(security_level, "PQC")
    db.save_email(
        recipient=sender_name, sender=sender_name, subject=f"To: {recipient_name} — {sent_subject}",
        plaintext=result.get("plaintext_str", ""), verified=True, folder="sent",
    )
    _refresh_inbox(sender_name)

    db.log_audit(sender_name, "send_email",
                 f"[{level_label}] To {recipient_name}: {subject[:50]}", _get_ip())

    return jsonify({"ok": True, "steps": _bytes_to_b64(result["steps"]),
                     "security_level": security_level})


@app.route("/api/send-forged", methods=["POST"])
def api_send_forged():
    data = request.get_json(force=True)
    sender_name = data.get("sender", "").strip().lower()
    recipient_name = data.get("recipient", "").strip().lower()
    subject = data.get("subject", "").strip()[:config.MAX_SUBJECT_LEN]
    body = data.get("body", "").strip()[:config.MAX_BODY_LEN]

    if sender_name not in clients:
        return jsonify({"error": f"Unknown sender '{sender_name}'"}), 404
    if recipient_name not in clients:
        return jsonify({"error": f"Unknown recipient '{recipient_name}'"}), 404
    if not subject or not body:
        return jsonify({"error": "Subject and body are required."}), 400

    forge_user = next((n for n in clients if n != sender_name), None)
    if not forge_user:
        return jsonify({"error": "Need at least 2 users for forgery demo."}), 400

    client = clients[sender_name]
    result = client.send_email_forged_with_log(
        recipient_name, subject, body, clients[forge_user].dilithium_sk, forge_user
    )

    pkg = result["package"]
    db.save_pending(
        recipient=recipient_name, sender=sender_name,
        encapsulated_key=pkg["encapsulated_key"], ciphertext=pkg["ciphertext"],
        nonce=pkg["nonce"], tag=pkg["tag"],
    )
    db.log_audit(sender_name, "send_forged", f"Forged sig demo to {recipient_name}", _get_ip())

    return jsonify({"ok": True, "steps": _bytes_to_b64(result["steps"])})


@app.route("/api/send-password", methods=["POST"])
def api_send_password():
    """Send a password-protected message (KDF instead of KEM)."""
    data = request.get_json(force=True)
    sender_name = data.get("sender", "").strip().lower()
    recipient_name = data.get("recipient", "").strip().lower()
    subject = data.get("subject", "").strip()[:config.MAX_SUBJECT_LEN]
    body = data.get("body", "").strip()[:config.MAX_BODY_LEN]
    password = data.get("password", "")

    if sender_name not in clients or recipient_name not in clients:
        return jsonify({"error": "Unknown user"}), 404
    if not subject or not body or not password:
        return jsonify({"error": "Subject, body, and password are required."}), 400

    client = clients[sender_name]
    result = client.send_email_password_protected_with_log(recipient_name, subject, body, password)

    pkg = result["package"]
    db.save_pending(
        recipient=recipient_name, sender=sender_name,
        encapsulated_key=pkg["encapsulated_key"], ciphertext=pkg["ciphertext"],
        nonce=pkg["nonce"], tag=pkg["tag"],
    )
    db.log_audit(sender_name, "send_password_protected", f"Password-protected to {recipient_name}", _get_ip())

    return jsonify({"ok": True, "steps": _bytes_to_b64(result["steps"])})


# ── Routes: Receive ──────────────────────────────────────────────────────────

@app.route("/api/receive/<username>", methods=["POST"])
def api_receive(username: str):
    if username not in clients:
        return jsonify({"error": f"Unknown user '{username}'"}), 404

    client = clients[username]
    result = client.receive_emails_with_log()

    for r in result["results"]:
        r["read"] = False
        subj = _extract_subject(r.get("plaintext"))
        email_id = db.save_email(
            recipient=username, sender=r.get("sender", "unknown"),
            plaintext=r.get("plaintext"), verified=r.get("verified", False),
            error=r.get("error"), subject=subj,
        )
        r["id"] = email_id
        r["subject"] = subj
        r["folder"] = "inbox"
        inboxes.setdefault(username, []).append(r)

    for mid in client.seen_message_ids:
        db.save_seen_id(username, mid)
    db.delete_pending(username)

    verified_count = sum(1 for r in result["results"] if r.get("verified"))
    failed_count = len(result["results"]) - verified_count
    if result["results"]:
        db.log_audit(username, "receive_email",
                     f"Received {len(result['results'])} ({verified_count} ok, {failed_count} failed)",
                     _get_ip())

    return jsonify({
        "ok": True,
        "steps": _bytes_to_b64(result["steps"]),
        "results": result["results"],
    })


# ── Routes: Tamper / Replay ──────────────────────────────────────────────────

@app.route("/api/tamper/<username>", methods=["POST"])
def api_tamper(username: str):
    if username not in clients:
        return jsonify({"error": f"Unknown user '{username}'"}), 404
    pending = mail_server.mailboxes.get(username, [])
    if not pending:
        return jsonify({"error": "No pending messages to tamper with."}), 400
    original_ct = bytearray(pending[0]["ciphertext"])
    original_ct[0] ^= 0xFF
    pending[0]["ciphertext"] = bytes(original_ct)
    db.log_audit(username, "tamper_demo", "Ciphertext tampered", _get_ip())
    return jsonify({"ok": True, "message": f"Tampered with the first pending message for {username}."})


@app.route("/api/replay/<username>", methods=["POST"])
def api_replay(username: str):
    if username not in clients:
        return jsonify({"error": f"Unknown user '{username}'"}), 404
    pending = mail_server.mailboxes.get(username, [])
    if not pending:
        return jsonify({"error": "No pending messages to replay."}), 400
    pending.append(dict(pending[0]))
    db.log_audit(username, "replay_demo", "Message replayed", _get_ip())
    return jsonify({"ok": True, "message": f"Replayed the first pending message for {username}."})


# ── Routes: Reply / Forward ─────────────────────────────────────────────────

@app.route("/api/reply", methods=["POST"])
def api_reply():
    """Pre-fill compose for reply."""
    data = request.get_json(force=True)
    original_sender = data.get("original_sender", "")
    original_subject = data.get("original_subject", "")
    original_body = data.get("original_body", "")
    subj = f"Re: {original_subject}" if not original_subject.startswith("Re:") else original_subject
    quoted = "\n".join(f"> {line}" for line in original_body.split("\n"))
    return jsonify({"recipient": original_sender, "subject": subj, "body": f"\n\n{quoted}"})


@app.route("/api/forward", methods=["POST"])
def api_forward():
    data = request.get_json(force=True)
    original_subject = data.get("original_subject", "")
    original_body = data.get("original_body", "")
    original_sender = data.get("original_sender", "")
    subj = f"Fwd: {original_subject}" if not original_subject.startswith("Fwd:") else original_subject
    body = f"\n\n--- Forwarded message from {original_sender} ---\n{original_body}"
    return jsonify({"subject": subj, "body": body})


# ── Routes: Drafts ───────────────────────────────────────────────────────────

@app.route("/api/drafts/<username>")
def api_drafts(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    return jsonify({"drafts": db.load_drafts(username)})


@app.route("/api/draft/<username>", methods=["POST"])
def api_save_draft(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    data = request.get_json(force=True)
    draft_id = db.save_draft(
        owner=username,
        recipient=data.get("recipient", ""),
        subject=data.get("subject", "")[:config.MAX_SUBJECT_LEN],
        body=data.get("body", "")[:config.MAX_BODY_LEN],
        draft_id=data.get("draft_id"),
    )
    return jsonify({"ok": True, "draft_id": draft_id})


@app.route("/api/draft/<username>/<int:draft_id>", methods=["DELETE"])
def api_delete_draft(username: str, draft_id: int):
    db.delete_draft(draft_id, username)
    return jsonify({"ok": True})


# ── Routes: Contacts ─────────────────────────────────────────────────────────

@app.route("/api/contacts/<username>")
def api_contacts(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    contacts = db.load_contacts(username)
    return jsonify({"contacts": contacts})


@app.route("/api/contacts/<username>", methods=["POST"])
def api_add_contact(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    target = data.get("username", "").strip().lower()
    if not name:
        return jsonify({"error": "Contact name is required."}), 400

    kyber_fp = ""
    dilithium_fp = ""
    if target in clients:
        kyber_fp = crypto_utils.key_fingerprint_short(clients[target].kyber_pk)
        dilithium_fp = crypto_utils.key_fingerprint_short(clients[target].dilithium_pk)

    cid = db.save_contact(owner=username, name=name, username=target,
                          kyber_fp=kyber_fp, dilithium_fp=dilithium_fp, notes=data.get("notes", ""))
    return jsonify({"ok": True, "contact_id": cid})


@app.route("/api/contacts/<username>/<int:contact_id>", methods=["DELETE"])
def api_delete_contact(username: str, contact_id: int):
    db.delete_contact(contact_id, username)
    return jsonify({"ok": True})


@app.route("/api/contacts/verify/<int:contact_id>", methods=["POST"])
def api_verify_contact(contact_id: int):
    data = request.get_json(force=True)
    db.update_contact_verified(contact_id, data.get("verified", True))
    return jsonify({"ok": True})


# ── Routes: Attachments ──────────────────────────────────────────────────────

@app.route("/api/attachments/<int:email_id>")
def api_get_attachments(email_id: int):
    return jsonify({"attachments": db.load_attachments(email_id)})


@app.route("/api/attachment/upload/<int:email_id>", methods=["POST"])
def api_upload_attachment(email_id: int):
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400
    f = request.files["file"]
    data = f.read()
    if len(data) > config.MAX_ATTACHMENT_BYTES:
        return jsonify({"error": f"File too large (max {config.MAX_ATTACHMENT_BYTES // 1024 // 1024}MB)."}), 400
    aid = db.save_attachment(email_id, f.filename or "file", f.mimetype or "application/octet-stream", data)
    return jsonify({"ok": True, "attachment_id": aid, "filename": f.filename, "size_bytes": len(data)})


@app.route("/api/attachment/download/<int:attachment_id>")
def api_download_attachment(attachment_id: int):
    att = db.get_attachment_data(attachment_id)
    if not att:
        return jsonify({"error": "Attachment not found."}), 404
    return send_file(io.BytesIO(att["data"]), download_name=att["filename"],
                     mimetype=att["mimetype"], as_attachment=True)


# ── Routes: Search ───────────────────────────────────────────────────────────

@app.route("/api/search/<username>")
def api_search(username: str):
    if username not in clients:
        return jsonify({"error": f"Unknown user '{username}'"}), 404
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"emails": inboxes.get(username, [])})
    results = db.search_emails(username, q)
    return jsonify({"emails": results})


# ── Routes: Read ─────────────────────────────────────────────────────────────

@app.route("/api/read/<username>/<int:email_id>", methods=["POST"])
def api_mark_read(username: str, email_id: int):
    if username not in clients:
        return jsonify({"error": f"Unknown user '{username}'"}), 404
    db.mark_read(email_id)
    for em in inboxes.get(username, []):
        if em.get("id") == email_id:
            em["read"] = True
            break
    return jsonify({"ok": True})


# ── Routes: Sessions ─────────────────────────────────────────────────────────

@app.route("/api/sessions/<username>")
def api_sessions(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    return jsonify({"sessions": db.load_sessions(username)})


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def api_revoke_session(session_id: str):
    db.delete_session(session_id)
    return jsonify({"ok": True})


# ── Routes: Audit Log ────────────────────────────────────────────────────────

@app.route("/api/audit/<username>")
def api_audit(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    limit = request.args.get("limit", 100, type=int)
    return jsonify({"log": db.load_audit_log(username, limit)})


# ── Routes: Settings ─────────────────────────────────────────────────────────

@app.route("/api/settings/<username>")
def api_get_settings(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    return jsonify({"settings": db.get_settings(username)})


@app.route("/api/settings/<username>", methods=["POST"])
def api_save_settings(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    data = request.get_json(force=True)
    db.save_settings(username, **data)
    return jsonify({"ok": True})


# ── Routes: Keys ─────────────────────────────────────────────────────────────

@app.route("/api/keys/<username>")
def api_keys(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    c = clients[username]
    return jsonify({
        "kyber_pk_fingerprint": crypto_utils.key_fingerprint(c.kyber_pk),
        "dilithium_pk_fingerprint": crypto_utils.key_fingerprint(c.dilithium_pk),
        "kyber_pk_bytes": len(c.kyber_pk),
        "kyber_sk_bytes": len(c.kyber_sk),
        "dilithium_pk_bytes": len(c.dilithium_pk),
        "dilithium_sk_bytes": len(c.dilithium_sk),
        "kem_algorithm": crypto_utils.KEM_ALG,
        "sig_algorithm": crypto_utils.SIG_ALG,
    })


@app.route("/api/keys/export/<username>/<key_type>")
def api_export_key(username: str, key_type: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    c = clients[username]
    key_map = {"kyber_pk": c.kyber_pk, "dilithium_pk": c.dilithium_pk}
    if key_type not in key_map:
        return jsonify({"error": "Invalid key type. Use kyber_pk or dilithium_pk."}), 400
    data = key_map[key_type]
    db.log_audit(username, "key_export", f"Exported {key_type}", _get_ip())
    return send_file(io.BytesIO(data), download_name=f"{username}_{key_type}.bin",
                     mimetype="application/octet-stream", as_attachment=True)


@app.route("/api/keys/verify", methods=["POST"])
def api_verify_keys():
    """Compare fingerprints of two users."""
    data = request.get_json(force=True)
    user_a = data.get("user_a", "").strip().lower()
    user_b = data.get("user_b", "").strip().lower()
    if user_a not in clients or user_b not in clients:
        return jsonify({"error": "Unknown user"}), 404
    return jsonify({
        "user_a": {
            "kyber_fingerprint": crypto_utils.key_fingerprint(clients[user_a].kyber_pk),
            "dilithium_fingerprint": crypto_utils.key_fingerprint(clients[user_a].dilithium_pk),
        },
        "user_b": {
            "kyber_fingerprint": crypto_utils.key_fingerprint(clients[user_b].kyber_pk),
            "dilithium_fingerprint": crypto_utils.key_fingerprint(clients[user_b].dilithium_pk),
        },
    })


# ── Routes: Benchmarks ──────────────────────────────────────────────────────

@app.route("/api/benchmarks")
def api_benchmarks():
    results = crypto_utils.run_benchmarks(iterations=5)
    return jsonify({"benchmarks": results})


# ── Routes: Register ─────────────────────────────────────────────────────────

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(force=True)
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    if not username:
        return jsonify({"error": "Username is required."}), 400
    if not username.isalnum() or len(username) > config.MAX_USERNAME_LEN:
        return jsonify({"error": "Username must be alphanumeric, max 32 chars."}), 400
    if username in clients:
        return jsonify({"error": f"User '{username}' already exists."}), 409

    keygen = Client.generate_keys_with_log()
    c = Client.from_keys(
        username=username, server=mail_server,
        kyber_pk=keygen["kyber_pk"], kyber_sk=keygen["kyber_sk"],
        dilithium_pk=keygen["dilithium_pk"], dilithium_sk=keygen["dilithium_sk"],
        rsa_pk=keygen["rsa_pk"], rsa_sk=keygen["rsa_sk"],
    )
    clients[username] = c
    inboxes[username] = []

    pw_hash = None
    if password:
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        pw_hash = ph.hash(password)

    db.save_user(username, c.kyber_pk, c.kyber_sk, c.dilithium_pk, c.dilithium_sk, pw_hash,
                 rsa_pk=c.rsa_pk, rsa_sk=c.rsa_sk)
    db.log_audit(username, "register", "User registered", _get_ip())

    return jsonify({"ok": True, "user": _user_info(username), "steps": keygen["steps"]})


# ── Routes: Undo Send ────────────────────────────────────────────────────────

@app.route("/api/undo-send/<pending_id>", methods=["POST"])
def api_undo_send(pending_id: str):
    """Cancel a pending send within the undo window."""
    if pending_id in undo_queue:
        info = undo_queue.pop(pending_id)
        recipient = info.get("recipient", "")
        if recipient in mail_server.mailboxes and mail_server.mailboxes[recipient]:
            mail_server.mailboxes[recipient].pop()
        return jsonify({"ok": True, "message": "Send cancelled."})
    return jsonify({"error": "Undo window expired or invalid ID."}), 400


# ── Routes: Report Export ────────────────────────────────────────────────────

@app.route("/api/report/<username>")
def api_report(username: str):
    """Generate an HTML security report for download."""
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    c = clients[username]
    audit = db.load_audit_log(username, 50)
    benchmarks = crypto_utils.run_benchmarks(3)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Security Report — {username}</title>
<style>body{{font-family:system-ui;max-width:800px;margin:40px auto;padding:20px;color:#222}}
h1{{color:#6c5ce7}}table{{width:100%;border-collapse:collapse;margin:16px 0}}
th,td{{padding:8px 12px;border:1px solid #ddd;text-align:left;font-size:13px}}
th{{background:#f0f0f0}}.section{{margin:24px 0}}.mono{{font-family:monospace;font-size:12px}}
</style></head><body>
<h1>Schrödinger Mail — Security Report</h1>
<p><strong>User:</strong> {username} | <strong>Generated:</strong> {__import__('datetime').datetime.now().isoformat()}</p>

<div class="section"><h2>Algorithms</h2>
<table><tr><th>Type</th><th>Algorithm</th></tr>
<tr><td>KEM</td><td>{crypto_utils.KEM_ALG}</td></tr>
<tr><td>Signature</td><td>{crypto_utils.SIG_ALG}</td></tr>
<tr><td>Symmetric</td><td>AES-256-GCM</td></tr></table></div>

<div class="section"><h2>Key Sizes</h2>
<table><tr><th>Key</th><th>Size (bytes)</th></tr>
<tr><td>Kyber Public Key</td><td>{len(c.kyber_pk)}</td></tr>
<tr><td>Kyber Secret Key</td><td>{len(c.kyber_sk)}</td></tr>
<tr><td>Dilithium Public Key</td><td>{len(c.dilithium_pk)}</td></tr>
<tr><td>Dilithium Secret Key</td><td>{len(c.dilithium_sk)}</td></tr></table></div>

<div class="section"><h2>Key Fingerprints</h2>
<p class="mono"><strong>Kyber:</strong> {crypto_utils.key_fingerprint(c.kyber_pk)}</p>
<p class="mono"><strong>Dilithium:</strong> {crypto_utils.key_fingerprint(c.dilithium_pk)}</p></div>

<div class="section"><h2>Performance Benchmarks (3 iterations)</h2>
<table><tr><th>Operation</th><th>Avg (ms)</th><th>Output Size</th></tr>
{"".join(f'<tr><td>{b["operation"]}</td><td>{b["avg_ms"]:.3f}</td><td>{b["size_bytes"]}</td></tr>' for b in benchmarks)}
</table></div>

<div class="section"><h2>Recent Audit Log</h2>
<table><tr><th>Action</th><th>Details</th><th>Timestamp</th></tr>
{"".join(f'<tr><td>{a["action"]}</td><td>{a["details"]}</td><td>{a["timestamp"]}</td></tr>' for a in audit[:20])}
</table></div>

</body></html>"""

    db.log_audit(username, "report_export", "Security report downloaded", _get_ip())
    return send_file(io.BytesIO(html.encode()), download_name=f"security_report_{username}.html",
                     mimetype="text/html", as_attachment=True)


# ── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  Schrödinger Mail — Quantum-Secure Email Client")
    print(f"  KEM : {crypto_utils.KEM_ALG}")
    print(f"  SIG : {crypto_utils.SIG_ALG}")
    print(f"  DEM : AES-256-GCM")
    print(f"  Users loaded: {', '.join(clients.keys())}")
    print(f"  Debug: {config.DEBUG}")
    print(f"  Open http://127.0.0.1:{config.PORT} in your browser.\n")
    app.run(debug=config.DEBUG, port=config.PORT)
