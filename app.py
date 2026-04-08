#!/usr/bin/env python3
"""
app.py — Flask Web Server for Schrödinger Mail
===========================================================
Full-featured email client with JWT authentication, folder management,
contacts, drafts, encrypted attachments, audit logging, rate limiting,
CSRF protection, WebSocket real-time delivery, multi-recipient encryption,
email threading, forward secrecy, and Prometheus metrics.
"""

from __future__ import annotations

import base64
import hashlib
import io
import logging
import os
import secrets
import time
import uuid
from functools import wraps
from typing import Any, Dict, List, Optional

from flask import (Flask, Response, jsonify, redirect, render_template,
                   request, send_file, session, url_for)

import auth as jwt_auth
import config
import crypto_utils
import database as db
import metrics
from client import Client
from logging_config import setup_logging
from server import Server

setup_logging()
logger = logging.getLogger(__name__)

# ── Flask app ────────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = config.MAX_ATTACHMENT_BYTES + 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"

# Rate limiting
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(get_remote_address, app=app,
                      default_limits=[config.RATE_LIMIT_DEFAULT],
                      storage_uri="memory://")
except Exception:
    limiter = None

# WebSocket support
socketio = None
try:
    from flask_socketio import SocketIO, emit, join_room
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
except ImportError:
    pass

# ── Global state ─────────────────────────────────────────────────────────────

mail_server = Server()
clients: Dict[str, Client] = {}
inboxes: Dict[str, list] = {}
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
        logger.info("No users found; waiting for registration.")
    logger.info("Bootstrap complete: %d users loaded", len(clients))

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


def _extract_header(plaintext: str, header: str) -> Optional[str]:
    for line in plaintext.split("\n"):
        if line.startswith(f"{header}: "):
            return line.split(f"{header}: ", 1)[1].strip()
        if line == "":
            break
    return None


def _validate_input(data: dict, *fields: str) -> Optional[str]:
    for f in fields:
        val = data.get(f, "")
        if isinstance(val, str):
            val = val.strip()
        if not val:
            return f"{f} is required."
    return None


def _get_ip() -> str:
    return request.headers.get("X-Real-IP") or request.remote_addr or ""


def _current_user() -> Optional[str]:
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        return jwt_auth.get_username_from_token(token)
    return session.get("username")


def _require_auth(f):
    """Decorator: require login via JWT or session."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        has_any_password = any(db.get_password_hash(u) for u in clients)
        if has_any_password:
            user = _current_user()
            if not user:
                return jsonify({"error": "Authentication required.", "login_required": True}), 401
        return f(*args, **kwargs)

    return wrapper


def _assert_own_user(username: str):
    """Return a 403 response if the authenticated user doesn't match username."""
    current = _current_user()
    if current and current != username:
        return jsonify({"error": "Access denied."}), 403
    return None


def _notify_ws(username: str, event: str, data: Any = None) -> None:
    """Send a WebSocket notification to a user's room."""
    if socketio:
        socketio.emit(event, data or {}, room=username)


def _get_p2p_contact_address(owner: str, recipient: str) -> Optional[str]:
    """
    Look up the P2P peer address for *recipient* from *owner*'s contacts.

    Returns a string like ``\"192.168.1.10:6001\"`` or ``None`` if not found.
    """
    if not config.P2P_ENABLED:
        return None
    try:
        contacts = db.load_contacts(owner)
    except Exception:
        return None
    for c in contacts:
        if c.get("username") == recipient and c.get("peer_address"):
            return str(c["peer_address"])
    return None


def _send_p2p_package(
    peer_address: str,
    recipient: str,
    sender: str,
    package: Dict[str, Any],
) -> Optional[str]:
    """
    Send an encrypted package directly to a peer node over HTTP.

    Returns ``None`` on success or an error string on failure.
    """
    import json
    import urllib.error
    import urllib.request

    url = f"http://{peer_address}/p2p/incoming"

    def _b64(b: bytes) -> str:
        return base64.b64encode(b).decode("ascii")

    payload = {
        "recipient": recipient,
        "sender": sender,
        "encapsulated_key": _b64(package["encapsulated_key"]),
        "ciphertext": _b64(package["ciphertext"]),
        "nonce": _b64(package["nonce"]),
        "tag": _b64(package["tag"]),
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
            if resp.status >= 400:
                return f"P2P peer returned HTTP {resp.status}"
    except urllib.error.URLError as exc:
        return f"Failed to contact P2P peer at {peer_address}: {exc}"
    except Exception as exc:  # pragma: no cover - defensive
        return f"Unexpected error contacting P2P peer at {peer_address}: {exc}"
    return None


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


# ── Request timing ───────────────────────────────────────────────────────────

@app.before_request
def _start_timer():
    request._start_time = time.perf_counter()


@app.after_request
def _record_duration(response):
    if hasattr(request, "_start_time"):
        duration = time.perf_counter() - request._start_time
        metrics.observe("request_duration_seconds", duration)
    return response


# ── Routes: Pages ────────────────────────────────────────────────────────────


@app.route("/")
def home():
    """Login / register landing page."""
    return render_template("home.html")


@app.route("/dashboard")
def dashboard():
    """Main React SPA — requires the user to be logged in."""
    static_path = os.path.join(app.root_path, "static", "index.html")
    if os.path.exists(static_path):
        return send_file(static_path)
    return render_template("home.html")


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
            metrics.inc("auth_login_failed_total")
            db.log_audit(username, "login_failed", "Wrong password", _get_ip())
            return jsonify({"error": "Invalid password."}), 401

    session["username"] = username
    sid = secrets.token_hex(16)
    session["session_id"] = sid
    db.save_session(sid, username, _get_ip(), request.user_agent.string)
    db.log_audit(username, "login", "Logged in", _get_ip())
    metrics.inc("auth_login_total")

    tokens = jwt_auth.create_token_pair(username)

    return jsonify({
        "ok": True,
        "user": _user_info(username),
        **tokens,
    })


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    username = session.get("username", "")
    sid = session.get("session_id", "")
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        jwt_auth.blacklist_token(token)
    if sid:
        db.delete_session(sid)
    if username:
        db.log_audit(username, "logout", "Logged out", _get_ip())
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/auth/refresh", methods=["POST"])
def api_refresh_token():
    """Refresh an access token using a refresh token."""
    data = request.get_json(force=True)
    refresh_token = data.get("refresh_token", "")
    result = jwt_auth.refresh_access_token(refresh_token)
    if not result:
        return jsonify({"error": "Invalid or expired refresh token."}), 401
    return jsonify(result)


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

    if config.ZERO_KNOWLEDGE_MODE:
        c = clients[username]
        blob = crypto_utils.encrypt_key_blob({
            "kyber_sk": c.kyber_sk,
            "dilithium_sk": c.dilithium_sk,
            "rsa_sk": c.rsa_sk or b"",
        }, password)
        db.save_encrypted_key_blob(username, blob)

    db.log_audit(username, "password_set", "Password created/changed", _get_ip())
    return jsonify({"ok": True})


@app.route("/api/auth/status")
def api_auth_status():
    has_any_password = any(db.get_password_hash(u) for u in clients)
    return jsonify({
        "auth_enabled": has_any_password,
        "logged_in": "username" in session or bool(_current_user()),
        "username": _current_user() or session.get("username", ""),
        "csrf_token": session.get("csrf_token", ""),
        "zero_knowledge_mode": config.ZERO_KNOWLEDGE_MODE,
        "forward_secrecy": config.FORWARD_SECRECY,
    })


# ── Routes: State ────────────────────────────────────────────────────────────

@app.route("/api/state")
@_require_auth
def api_state():
    return jsonify({
        "kem_algorithm": crypto_utils.KEM_ALG,
        "sig_algorithm": crypto_utils.SIG_ALG,
        "dem_algorithm": "AES-256-GCM",
        "users": {name: _user_info(name) for name in clients},
        "features": {
            "zero_knowledge": config.ZERO_KNOWLEDGE_MODE,
            "forward_secrecy": config.FORWARD_SECRECY,
            "websockets": socketio is not None,
            "multi_recipient": True,
            "encrypted_attachments": True,
            "email_threading": True,
        },
        "mode": "p2p" if config.P2P_ENABLED else "demo",
        "local_username": _current_user() or session.get("username", ""),
    })


@app.route("/api/inbox/<username>")
@_require_auth
def api_inbox(username: str):
    if username not in clients:
        return jsonify({"error": f"Unknown user '{username}'"}), 404
    err = _assert_own_user(username)
    if err:
        return err
    return jsonify({"emails": inboxes.get(username, [])})


# ── Routes: Folders ──────────────────────────────────────────────────────────

@app.route("/api/folders/<username>")
@_require_auth
def api_folders(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    err = _assert_own_user(username)
    if err:
        return err
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
@_require_auth
def api_emails_by_folder(username: str, folder: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    err = _assert_own_user(username)
    if err:
        return err
    emails = db.load_emails_by_folder(username, folder)
    return jsonify({"emails": emails})


@app.route("/api/move/<username>/<int:email_id>", methods=["POST"])
@_require_auth
def api_move_email(username: str, email_id: int):
    err = _assert_own_user(username)
    if err:
        return err
    data = request.get_json(force=True)
    folder = data.get("folder", "").strip()
    if folder not in ("inbox", "sent", "archive", "trash"):
        return jsonify({"error": "Invalid folder."}), 400
    db.move_email(email_id, folder)
    _refresh_inbox(username)
    db.log_audit(username, "move_email", f"Moved email {email_id} to {folder}", _get_ip())
    return jsonify({"ok": True})


@app.route("/api/delete/<username>/<int:email_id>", methods=["POST"])
@_require_auth
def api_delete_email(username: str, email_id: int):
    err = _assert_own_user(username)
    if err:
        return err
    db.move_email(email_id, "trash")
    _refresh_inbox(username)
    return jsonify({"ok": True})


@app.route("/api/delete-permanent/<username>/<int:email_id>", methods=["DELETE"])
@_require_auth
def api_delete_permanent(username: str, email_id: int):
    err = _assert_own_user(username)
    if err:
        return err
    db.delete_email_permanent(email_id)
    _refresh_inbox(username)
    return jsonify({"ok": True})


@app.route("/api/empty-trash/<username>", methods=["DELETE"])
@_require_auth
def api_empty_trash(username: str):
    err = _assert_own_user(username)
    if err:
        return err
    count = db.empty_trash(username)
    _refresh_inbox(username)
    db.log_audit(username, "empty_trash", f"Permanently deleted {count} emails", _get_ip())
    return jsonify({"ok": True, "deleted": count})


def _refresh_inbox(username: str) -> None:
    inboxes[username] = db.load_emails(username)


# ── Routes: Send ─────────────────────────────────────────────────────────────

@app.route("/api/send", methods=["POST"])
@_require_auth
def api_send():
    data = request.get_json(force=True)
    sender_name = data.get("sender", "").strip().lower()
    recipient_name = data.get("recipient", "").strip().lower()
    recipients = data.get("recipients", [])
    subject = data.get("subject", "").strip()[:config.MAX_SUBJECT_LEN]
    body = data.get("body", "").strip()[:config.MAX_BODY_LEN]
    encrypt_subject = data.get("encrypt_subject", False)
    security_level = data.get("security_level", 2)
    in_reply_to = data.get("in_reply_to")
    thread_id = data.get("thread_id")

    if sender_name not in clients:
        return jsonify({"error": f"Unknown sender '{sender_name}'"}), 404
    err = _assert_own_user(sender_name)
    if err:
        return err
    if not subject or not body:
        return jsonify({"error": "Subject and body are required."}), 400

    # Multi-recipient support
    if recipients and len(recipients) > 1:
        for r in recipients:
            if r.strip().lower() not in clients:
                return jsonify({"error": f"Unknown recipient '{r}'"}), 404
        client = clients[sender_name]
        sig = db.get_settings(sender_name).get("signature", "")
        if sig:
            body = body + "\n\n-- \n" + sig
        result = client.send_email_multi_recipient(
            [r.strip().lower() for r in recipients], subject, body, encrypt_subject,
        )
        for r in recipients:
            r_lower = r.strip().lower()
            _notify_ws(r_lower, "new_mail", {"from": sender_name})
        metrics.inc("emails_sent_total")
        db.log_audit(sender_name, "send_multi", f"To {','.join(recipients)}: {subject[:50]}", _get_ip())
        return jsonify({"ok": True, "steps": _bytes_to_b64(result["steps"]), "multi": True})

    if not recipient_name:
        recipient_name = (recipients[0] if recipients else "").strip().lower()
    if recipient_name not in clients:
        return jsonify({"error": f"Unknown recipient '{recipient_name}'"}), 404

    client = clients[sender_name]
    sig = db.get_settings(sender_name).get("signature", "")
    if sig:
        body = body + "\n\n-- \n" + sig

    if security_level == 3:
        recipient_rsa_pk = clients[recipient_name].rsa_pk
        result = client.send_email_hybrid_with_log(
            recipient_name, subject, body, recipient_rsa_pk, encrypt_subject
        )
    elif config.FORWARD_SECRECY and security_level == 2:
        result = client.send_email_with_forward_secrecy(recipient_name, subject, body)
    else:
        result = client.send_email_with_log(recipient_name, subject, body, encrypt_subject)

    pkg = result["package"]

    # If P2P LAN mode is enabled and we have a peer address configured for
    # this recipient, send the package directly to the peer node instead of
    # using the in-memory demo server.
    peer_address = _get_p2p_contact_address(sender_name, recipient_name)
    if config.P2P_ENABLED and peer_address:
        error = _send_p2p_package(peer_address, recipient_name, sender_name, pkg)
        if error:
            return jsonify({"error": error}), 502
    else:
        # Demo / central mode: store pending package locally.
        db.save_pending(
            recipient=recipient_name,
            sender=sender_name,
            encapsulated_key=pkg["encapsulated_key"],
            ciphertext=pkg["ciphertext"],
            nonce=pkg["nonce"],
            tag=pkg["tag"],
        )

    sent_subject = subject if not encrypt_subject else result.get("subject", subject)
    level_label = {1: "Password", 2: "PQC", 3: "Hybrid RSA+Kyber"}.get(security_level, "PQC")
    if config.FORWARD_SECRECY and security_level == 2:
        level_label = "PQC+FS"

    db.save_email(
        recipient=sender_name, sender=sender_name,
        subject=f"To: {recipient_name} — {sent_subject}",
        plaintext=result.get("plaintext_str", ""), verified=True, folder="sent",
        thread_id=thread_id, in_reply_to=in_reply_to,
    )
    _refresh_inbox(sender_name)
    _notify_ws(recipient_name, "new_mail", {"from": sender_name})

    db.log_audit(sender_name, "send_email",
                 f"[{level_label}] To {recipient_name}: {subject[:50]}", _get_ip())
    metrics.inc("emails_sent_total")

    return jsonify({"ok": True, "steps": _bytes_to_b64(result["steps"]),
                     "security_level": security_level})


@app.route("/api/send-forged", methods=["POST"])
@_require_auth
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
    # Forgery demo is always a local / demo operation; do not use P2P path.
    db.save_pending(
        recipient=recipient_name,
        sender=sender_name,
        encapsulated_key=pkg["encapsulated_key"],
        ciphertext=pkg["ciphertext"],
        nonce=pkg["nonce"],
        tag=pkg["tag"],
    )
    db.log_audit(sender_name, "send_forged", f"Forged sig demo to {recipient_name}", _get_ip())

    return jsonify({"ok": True, "steps": _bytes_to_b64(result["steps"])})


@app.route("/api/send-password", methods=["POST"])
@_require_auth
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
    err = _assert_own_user(sender_name)
    if err:
        return err
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
    metrics.inc("emails_sent_total")

    return jsonify({"ok": True, "steps": _bytes_to_b64(result["steps"])})


# ── Routes: Receive ──────────────────────────────────────────────────────────

@app.route("/api/receive/<username>", methods=["POST"])
@_require_auth
def api_receive(username: str):
    if username not in clients:
        return jsonify({"error": f"Unknown user '{username}'"}), 404
    err = _assert_own_user(username)
    if err:
        return err

    client = clients[username]
    result = client.receive_emails_with_log()

    for r in result["results"]:
        r["read"] = False
        subj = _extract_subject(r.get("plaintext"))
        thread_id = _extract_header(r.get("plaintext", ""), "Thread-ID")
        in_reply_to = _extract_header(r.get("plaintext", ""), "In-Reply-To")
        email_id = db.save_email(
            recipient=username, sender=r.get("sender", "unknown"),
            plaintext=r.get("plaintext"), verified=r.get("verified", False),
            error=r.get("error"), subject=subj,
            thread_id=thread_id, in_reply_to=in_reply_to,
        )
        r["id"] = email_id
        r["subject"] = subj
        r["folder"] = "inbox"
        r["thread_id"] = thread_id
        r["in_reply_to"] = in_reply_to
        inboxes.setdefault(username, []).append(r)

        if not r.get("verified"):
            if r.get("error") and "tampered" in r["error"].lower():
                metrics.inc("tamper_detected_total")
            elif r.get("error") and "signature" in r["error"].lower():
                metrics.inc("forge_detected_total")
            elif r.get("error") and "replay" in r["error"].lower():
                metrics.inc("replay_detected_total")
            metrics.inc("emails_failed_total")
        else:
            metrics.inc("emails_received_total")

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


# ── Routes: Threading ────────────────────────────────────────────────────────

@app.route("/api/thread/<thread_id>")
def api_thread(thread_id: str):
    """Load all emails in a conversation thread."""
    emails = db.load_thread(thread_id)
    return jsonify({"thread_id": thread_id, "emails": emails})


# ── Routes: Tamper / Replay ──────────────────────────────────────────────────

@app.route("/api/tamper/<username>", methods=["POST"])
@_require_auth
def api_tamper(username: str):
    if username not in clients:
        return jsonify({"error": f"Unknown user '{username}'"}), 404
    err = _assert_own_user(username)
    if err:
        return err
    pending = mail_server.mailboxes.get(username, [])
    if not pending:
        return jsonify({"error": "No pending messages to tamper with."}), 400
    original_ct = bytearray(pending[0]["ciphertext"])
    original_ct[0] ^= 0xFF
    pending[0]["ciphertext"] = bytes(original_ct)
    db.log_audit(username, "tamper_demo", "Ciphertext tampered", _get_ip())
    return jsonify({"ok": True, "message": f"Tampered with the first pending message for {username}."})


@app.route("/api/replay/<username>", methods=["POST"])
@_require_auth
def api_replay(username: str):
    if username not in clients:
        return jsonify({"error": f"Unknown user '{username}'"}), 404
    err = _assert_own_user(username)
    if err:
        return err
    pending = mail_server.mailboxes.get(username, [])
    if not pending:
        return jsonify({"error": "No pending messages to replay."}), 400
    pending.append(dict(pending[0]))
    db.log_audit(username, "replay_demo", "Message replayed", _get_ip())
    return jsonify({"ok": True, "message": f"Replayed the first pending message for {username}."})


# ── Routes: Verification Details ──────────────────────────────────────────────

@app.route("/api/verify-details/<username>/<int:email_id>")
@_require_auth
def api_verify_details(username: str, email_id: int):
    """Return per-message cryptographic verification evidence."""
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    err = _assert_own_user(username)
    if err:
        return err

    c = clients[username]
    emails = db.load_emails(username)
    email = next((e for e in emails if e.get("id") == email_id), None)
    if not email:
        return jsonify({"error": "Email not found"}), 404

    plaintext = email.get("plaintext", "")
    verified = email.get("verified", False)
    error_msg = email.get("error", "")
    sender_name = email.get("sender", "unknown")

    message_id = _extract_header(plaintext or "", "Message-ID")
    timestamp = _extract_header(plaintext or "", "Timestamp")

    replay_cached = message_id in c.seen_message_ids if message_id else False
    sender_known = sender_name in clients

    sender_fingerprints = {}
    if sender_known:
        sc = clients[sender_name]
        sender_fingerprints = {
            "kyber": crypto_utils.key_fingerprint(sc.kyber_pk),
            "dilithium": crypto_utils.key_fingerprint(sc.dilithium_pk),
        }

    checks = []
    if verified:
        checks.append({"check": "KEM Decapsulation", "status": "pass",
                        "detail": f"Kyber768 shared secret recovered ({crypto_utils.KEM_ALG})"})
        checks.append({"check": "AES-GCM Decryption", "status": "pass",
                        "detail": "Ciphertext decrypted, GCM authentication tag valid"})
        checks.append({"check": "Signature Verification", "status": "pass",
                        "detail": f"Dilithium3 signature verified against {sender_name}'s public key"})
        checks.append({"check": "Replay Check", "status": "pass",
                        "detail": f"Message-ID {message_id or 'N/A'} is unique (first seen)"})
        checks.append({"check": "Integrity", "status": "pass",
                        "detail": "No modification detected — plaintext matches authenticated decryption"})
    else:
        err_lower = (error_msg or "").lower()
        if "tamper" in err_lower or "corrupt" in err_lower or "tag" in err_lower:
            checks.append({"check": "KEM Decapsulation", "status": "pass",
                            "detail": "Shared secret recovered"})
            checks.append({"check": "AES-GCM Decryption", "status": "fail",
                            "detail": "GCM authentication tag mismatch — ciphertext was modified"})
            checks.append({"check": "Integrity", "status": "fail",
                            "detail": "Ciphertext tampering detected"})
        elif "signature" in err_lower or "forg" in err_lower:
            checks.append({"check": "KEM Decapsulation", "status": "pass",
                            "detail": "Shared secret recovered"})
            checks.append({"check": "AES-GCM Decryption", "status": "pass",
                            "detail": "Ciphertext decrypted successfully"})
            checks.append({"check": "Signature Verification", "status": "fail",
                            "detail": "Dilithium3 signature does NOT match sender's registered public key"})
        elif "replay" in err_lower:
            checks.append({"check": "KEM Decapsulation", "status": "pass",
                            "detail": "Shared secret recovered"})
            checks.append({"check": "AES-GCM Decryption", "status": "pass",
                            "detail": "Ciphertext decrypted successfully"})
            checks.append({"check": "Signature Verification", "status": "pass",
                            "detail": "Signature valid"})
            checks.append({"check": "Replay Check", "status": "fail",
                            "detail": f"Message-ID {message_id or 'N/A'} already in seen-ID cache"})
        else:
            checks.append({"check": "Decryption", "status": "fail",
                            "detail": error_msg or "Unknown decryption failure"})

    return jsonify({
        "email_id": email_id,
        "verified": verified,
        "error": error_msg,
        "sender": sender_name,
        "message_id": message_id,
        "timestamp": timestamp,
        "algorithms": {
            "kem": crypto_utils.KEM_ALG,
            "sig": crypto_utils.SIG_ALG,
            "dem": "AES-256-GCM",
        },
        "key_sizes": {
            "kyber_pk": len(c.kyber_pk),
            "kyber_sk": len(c.kyber_sk),
            "dilithium_pk": len(c.dilithium_pk),
            "dilithium_sk": len(c.dilithium_sk),
        },
        "sender_fingerprints": sender_fingerprints,
        "replay_cache_hit": replay_cached,
        "checks": checks,
    })


# ── Routes: Key Rotation ─────────────────────────────────────────────────────

@app.route("/api/keys/rotate/<username>", methods=["POST"])
@_require_auth
def api_rotate_keys(username: str):
    """Regenerate a user's Kyber and Dilithium keypairs (TOFU demo)."""
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    err = _assert_own_user(username)
    if err:
        return err

    c = clients[username]
    old_kyber_fp = crypto_utils.key_fingerprint(c.kyber_pk)
    old_dilithium_fp = crypto_utils.key_fingerprint(c.dilithium_pk)

    keygen = Client.generate_keys_with_log()
    c.kyber_pk = keygen["kyber_pk"]
    c.kyber_sk = keygen["kyber_sk"]
    c.dilithium_pk = keygen["dilithium_pk"]
    c.dilithium_sk = keygen["dilithium_sk"]
    if keygen.get("rsa_pk"):
        c.rsa_pk = keygen["rsa_pk"]
        c.rsa_sk = keygen["rsa_sk"]

    db.save_user(username, c.kyber_pk, c.kyber_sk, c.dilithium_pk, c.dilithium_sk,
                 db.get_password_hash(username),
                 rsa_pk=c.rsa_pk, rsa_sk=c.rsa_sk)

    new_kyber_fp = crypto_utils.key_fingerprint(c.kyber_pk)
    new_dilithium_fp = crypto_utils.key_fingerprint(c.dilithium_pk)

    db.log_audit(username, "key_rotation", f"Keys rotated. Kyber: {old_kyber_fp[:16]}→{new_kyber_fp[:16]}", _get_ip())

    return jsonify({
        "ok": True,
        "old_fingerprints": {"kyber": old_kyber_fp, "dilithium": old_dilithium_fp},
        "new_fingerprints": {"kyber": new_kyber_fp, "dilithium": new_dilithium_fp},
        "steps": keygen["steps"],
        "user": _user_info(username),
    })


# ── Routes: Network Trace ────────────────────────────────────────────────────

@app.route("/api/network-trace/<username>")
@_require_auth
def api_network_trace(username: str):
    """Return recent network-level delivery events for a user."""
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    err = _assert_own_user(username)
    if err:
        return err

    audit_entries = db.load_audit_log(username, 50)
    trace_events = []
    for entry in audit_entries:
        action = entry.get("action", "")
        if action in ("send_email", "send_multi", "send_forged", "send_password_protected",
                       "receive_email", "p2p_received", "p2p_sent", "tamper_demo", "replay_demo"):
            transport = "p2p" if "p2p" in action else "server"
            trace_events.append({
                "action": action,
                "details": entry.get("details", ""),
                "ip": entry.get("ip_address", ""),
                "timestamp": entry.get("timestamp", ""),
                "transport": transport,
            })

    is_p2p = config.P2P_ENABLED
    return jsonify({
        "events": trace_events,
        "mode": "p2p" if is_p2p else "demo",
        "local_address": f"127.0.0.1:{config.PORT}",
    })


# ── Routes: Demo Report Export ───────────────────────────────────────────────

@app.route("/api/demo-report/<username>")
@_require_auth
def api_demo_report(username: str):
    """Generate a comprehensive demo evidence report with all security data."""
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    err = _assert_own_user(username)
    if err:
        return err

    c = clients[username]
    audit = db.load_audit_log(username, 100)
    benchmarks = crypto_utils.run_benchmarks(3)
    emails_all = db.load_emails(username)

    attack_summary = {"tamper": 0, "forge": 0, "replay": 0, "verified": 0, "total": 0}
    for em in emails_all:
        attack_summary["total"] += 1
        if em.get("verified"):
            attack_summary["verified"] += 1
        else:
            err = (em.get("error") or "").lower()
            if "tamper" in err:
                attack_summary["tamper"] += 1
            elif "signature" in err or "forg" in err:
                attack_summary["forge"] += 1
            elif "replay" in err:
                attack_summary["replay"] += 1

    all_users_info = {}
    for uname, uclient in clients.items():
        all_users_info[uname] = {
            "kyber_fingerprint": crypto_utils.key_fingerprint(uclient.kyber_pk),
            "dilithium_fingerprint": crypto_utils.key_fingerprint(uclient.dilithium_pk),
            "kyber_pk_bytes": len(uclient.kyber_pk),
            "dilithium_pk_bytes": len(uclient.dilithium_pk),
        }

    report_json = {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "user": username,
        "algorithms": {
            "kem": crypto_utils.KEM_ALG,
            "sig": crypto_utils.SIG_ALG,
            "dem": "AES-256-GCM",
        },
        "features": {
            "zero_knowledge": config.ZERO_KNOWLEDGE_MODE,
            "forward_secrecy": config.FORWARD_SECRECY,
            "p2p_enabled": config.P2P_ENABLED,
        },
        "users": all_users_info,
        "attack_summary": attack_summary,
        "benchmarks": benchmarks,
        "audit_log": audit[:30],
    }

    import json as json_mod
    dt = __import__("datetime").datetime.now()

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Schrödinger Mail — Demo Evidence Report</title>
<style>
body{{font-family:'Inter',system-ui,sans-serif;max-width:900px;margin:40px auto;padding:20px;color:#1f2328;background:#f6f8fa;line-height:1.6}}
h1{{color:#0a0c10;font-size:22px;border-bottom:2px solid #4493f8;padding-bottom:8px}}
h2{{color:#1f2328;font-size:16px;margin-top:28px;margin-bottom:8px}}
h3{{font-size:14px;color:#636e7b;margin-top:20px;margin-bottom:6px}}
table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:13px}}
th,td{{padding:8px 12px;border:1px solid #d1d9e0;text-align:left}}
th{{background:#e8ebef;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:0.5px}}
.pass{{color:#1a7f37;font-weight:600}}.fail{{color:#cf222e;font-weight:600}}
.mono{{font-family:'JetBrains Mono',monospace;font-size:11px}}
.section{{margin:24px 0;padding:16px;background:#fff;border:1px solid #d1d9e0;border-radius:8px}}
.summary-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}}
.summary-card{{background:#fff;border:1px solid #d1d9e0;border-radius:8px;padding:16px;text-align:center}}
.summary-card .num{{font-size:28px;font-weight:700;color:#4493f8}}
.summary-card .label{{font-size:11px;color:#636e7b;text-transform:uppercase;letter-spacing:0.5px;margin-top:4px}}
pre{{background:#0a0c10;color:#cdd6e0;padding:12px;border-radius:6px;font-size:11px;overflow-x:auto}}
.badge{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600}}
.badge-pass{{background:#dafbe1;color:#1a7f37}}.badge-fail{{background:#ffebe9;color:#cf222e}}
.footer{{margin-top:32px;padding-top:16px;border-top:1px solid #d1d9e0;font-size:11px;color:#636e7b;text-align:center}}
</style></head><body>
<h1>Schrödinger Mail — Demo Evidence Report</h1>
<p><strong>User:</strong> {username} &nbsp;|&nbsp; <strong>Generated:</strong> {dt.strftime('%Y-%m-%d %H:%M:%S')} &nbsp;|&nbsp;
<strong>Project:</strong> Cryptography & Network Security</p>

<div class="summary-grid">
<div class="summary-card"><div class="num">{attack_summary['total']}</div><div class="label">Total Messages</div></div>
<div class="summary-card"><div class="num pass">{attack_summary['verified']}</div><div class="label">Verified</div></div>
<div class="summary-card"><div class="num fail">{attack_summary['tamper']+attack_summary['forge']+attack_summary['replay']}</div><div class="label">Attacks Detected</div></div>
<div class="summary-card"><div class="num">{len(list(clients.keys()))}</div><div class="label">Users</div></div>
</div>

<div class="section">
<h2>Cryptographic Algorithms</h2>
<table>
<tr><th>Component</th><th>Algorithm</th><th>NIST Standard</th><th>Security Level</th></tr>
<tr><td>Key Encapsulation (KEM)</td><td>{crypto_utils.KEM_ALG}</td><td>FIPS 203 (ML-KEM)</td><td>Level 3 (192-bit)</td></tr>
<tr><td>Digital Signature</td><td>{crypto_utils.SIG_ALG}</td><td>FIPS 204 (ML-DSA)</td><td>Level 3 (192-bit)</td></tr>
<tr><td>Symmetric Encryption</td><td>AES-256-GCM</td><td>FIPS 197 + SP 800-38D</td><td>256-bit</td></tr>
<tr><td>Key Derivation (Level 1)</td><td>scrypt</td><td>RFC 7914</td><td>Password-based</td></tr>
</table></div>

<div class="section">
<h2>Attack Detection Summary</h2>
<table>
<tr><th>Attack Type</th><th>Defense Mechanism</th><th>Detected Count</th><th>Status</th></tr>
<tr><td>Ciphertext Tampering</td><td>AES-256-GCM authentication tag</td><td>{attack_summary['tamper']}</td>
<td><span class="badge {'badge-pass' if attack_summary['tamper']>0 else 'badge-fail'}">{'TESTED' if attack_summary['tamper']>0 else 'NOT TESTED'}</span></td></tr>
<tr><td>Signature Forgery</td><td>Dilithium3 signature verification</td><td>{attack_summary['forge']}</td>
<td><span class="badge {'badge-pass' if attack_summary['forge']>0 else 'badge-fail'}">{'TESTED' if attack_summary['forge']>0 else 'NOT TESTED'}</span></td></tr>
<tr><td>Replay Attack</td><td>Message-ID seen-cache tracking</td><td>{attack_summary['replay']}</td>
<td><span class="badge {'badge-pass' if attack_summary['replay']>0 else 'badge-fail'}">{'TESTED' if attack_summary['replay']>0 else 'NOT TESTED'}</span></td></tr>
</table></div>

<div class="section">
<h2>Key Sizes & Fingerprints</h2>
{"".join(f'''<h3>{uname.capitalize()}</h3>
<table><tr><th>Key</th><th>Size (bytes)</th><th>SHA-256 Fingerprint</th></tr>
<tr><td>Kyber Public Key</td><td>{info["kyber_pk_bytes"]}</td><td class="mono">{info["kyber_fingerprint"][:48]}...</td></tr>
<tr><td>Dilithium Public Key</td><td>{info["dilithium_pk_bytes"]}</td><td class="mono">{info["dilithium_fingerprint"][:48]}...</td></tr>
</table>''' for uname, info in all_users_info.items())}
</div>

<div class="section">
<h2>Performance Benchmarks (3 iterations)</h2>
<table><tr><th>Operation</th><th>Avg (ms)</th><th>Output Size (bytes)</th></tr>
{"".join(f'<tr><td>{b["operation"]}</td><td class="mono">{b["avg_ms"]:.3f}</td><td class="mono">{b["size_bytes"]:,}</td></tr>' for b in benchmarks)}
</table></div>

<div class="section">
<h2>Features Configuration</h2>
<table><tr><th>Feature</th><th>Status</th></tr>
<tr><td>Zero-Knowledge Mode</td><td>{"Enabled" if config.ZERO_KNOWLEDGE_MODE else "Disabled"}</td></tr>
<tr><td>Forward Secrecy</td><td>{"Enabled" if config.FORWARD_SECRECY else "Disabled"}</td></tr>
<tr><td>P2P LAN Delivery</td><td>{"Enabled" if config.P2P_ENABLED else "Disabled"}</td></tr>
<tr><td>WebSocket Real-time</td><td>{"Enabled" if socketio else "Disabled"}</td></tr>
<tr><td>Encrypted Attachments</td><td>Enabled</td></tr>
<tr><td>Email Threading</td><td>Enabled</td></tr>
</table></div>

<div class="section">
<h2>Audit Trail (last 30 events)</h2>
<table><tr><th>Action</th><th>Details</th><th>IP</th><th>Timestamp</th></tr>
{"".join(f'<tr><td>{a["action"]}</td><td>{a["details"][:80]}</td><td class="mono">{a["ip_address"]}</td><td class="mono">{a["timestamp"]}</td></tr>' for a in audit[:30])}
</table></div>

<div class="section">
<h2>Machine-Readable Data (JSON)</h2>
<pre>{json_mod.dumps(report_json, indent=2, default=str)}</pre>
</div>

<div class="footer">
Schrödinger Mail — Quantum-Secure Email Client | Cryptography & Network Security Project | {dt.strftime('%Y')}
</div>
</body></html>"""

    db.log_audit(username, "demo_report_export", "Demo evidence report downloaded", _get_ip())
    return send_file(
        io.BytesIO(html.encode()),
        download_name=f"demo_evidence_report_{username}_{dt.strftime('%Y%m%d_%H%M%S')}.html",
        mimetype="text/html",
        as_attachment=True,
    )


# ── Routes: P2P LAN Mode ─────────────────────────────────────────────────────


@app.route("/p2p/incoming", methods=["POST"])
def p2p_incoming():
    """
    Receive an encrypted package from a peer node on the LAN.

    The payload is expected to be JSON with base64-encoded fields:
        recipient, sender, encapsulated_key, ciphertext, nonce, tag
    """
    if not config.P2P_ENABLED:
        return jsonify({"error": "P2P mode is disabled on this node."}), 404

    data = request.get_json(force=True)
    recipient = data.get("recipient", "").strip().lower()
    sender = data.get("sender", "").strip().lower()
    enc_b64 = data.get("encapsulated_key")
    ct_b64 = data.get("ciphertext")
    nonce_b64 = data.get("nonce")
    tag_b64 = data.get("tag")

    if not recipient or not sender:
        return jsonify({"error": "recipient and sender are required."}), 400
    if recipient not in clients:
        return jsonify({"error": f"Unknown local recipient '{recipient}'"}), 404
    if not all([enc_b64, ct_b64, nonce_b64, tag_b64]):
        return jsonify({"error": "Missing encrypted package fields."}), 400

    try:
        encapsulated_key = base64.b64decode(enc_b64)
        ciphertext = base64.b64decode(ct_b64)
        nonce = base64.b64decode(nonce_b64)
        tag = base64.b64decode(tag_b64)
    except Exception as exc:
        return jsonify({"error": f"Invalid base64 in package: {exc}"}), 400

    package = {
        "encapsulated_key": encapsulated_key,
        "ciphertext": ciphertext,
        "nonce": nonce,
        "tag": tag,
    }

    try:
        mail_server.send_message(sender=sender, recipient=recipient, package=package)
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 400

    # Persist a pending record so tests and tooling can inspect queued messages.
    db.save_pending(
        recipient=recipient,
        sender=sender,
        encapsulated_key=encapsulated_key,
        ciphertext=ciphertext,
        nonce=nonce,
        tag=tag,
    )
    db.log_audit(recipient, "p2p_incoming", f"P2P message from {sender}", _get_ip())

    return jsonify({"ok": True})


# ── Routes: Reply / Forward ─────────────────────────────────────────────────

@app.route("/api/reply", methods=["POST"])
def api_reply():
    data = request.get_json(force=True)
    original_sender = data.get("original_sender", "")
    original_subject = data.get("original_subject", "")
    original_body = data.get("original_body", "")
    original_thread_id = data.get("thread_id")
    original_message_id = data.get("message_id")
    subj = f"Re: {original_subject}" if not original_subject.startswith("Re:") else original_subject
    quoted = "\n".join(f"> {line}" for line in original_body.split("\n"))
    return jsonify({
        "recipient": original_sender, "subject": subj,
        "body": f"\n\n{quoted}",
        "thread_id": original_thread_id,
        "in_reply_to": original_message_id,
    })


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
@_require_auth
def api_drafts(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    err = _assert_own_user(username)
    if err:
        return err
    return jsonify({"drafts": db.load_drafts(username)})


@app.route("/api/draft/<username>", methods=["POST"])
@_require_auth
def api_save_draft(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    err = _assert_own_user(username)
    if err:
        return err
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
@_require_auth
def api_delete_draft(username: str, draft_id: int):
    err = _assert_own_user(username)
    if err:
        return err
    db.delete_draft(draft_id, username)
    return jsonify({"ok": True})


# ── Routes: Contacts ─────────────────────────────────────────────────────────

@app.route("/api/contacts/<username>")
@_require_auth
def api_contacts(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    err = _assert_own_user(username)
    if err:
        return err
    contacts = db.load_contacts(username)
    return jsonify({"contacts": contacts})


@app.route("/api/contacts/<username>", methods=["POST"])
@_require_auth
def api_add_contact(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    err = _assert_own_user(username)
    if err:
        return err
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

    cid = db.save_contact(
        owner=username,
        name=name,
        username=target,
        kyber_fp=kyber_fp,
        dilithium_fp=dilithium_fp,
        notes=data.get("notes", ""),
        peer_address=data.get("peer_address", "").strip(),
        device_label=data.get("device_label", "").strip(),
    )
    return jsonify({"ok": True, "contact_id": cid})


@app.route("/api/contacts/<username>/<int:contact_id>", methods=["DELETE"])
@_require_auth
def api_delete_contact(username: str, contact_id: int):
    err = _assert_own_user(username)
    if err:
        return err
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

    encrypted_blob, file_key = crypto_utils.encrypt_attachment(data)
    aid = db.save_attachment(
        email_id, f.filename or "file",
        f.mimetype or "application/octet-stream",
        encrypted_blob, encryption_key=file_key,
    )
    return jsonify({
        "ok": True, "attachment_id": aid,
        "filename": f.filename, "size_bytes": len(data),
        "encrypted": True,
    })


@app.route("/api/attachment/download/<int:attachment_id>")
def api_download_attachment(attachment_id: int):
    att = db.get_attachment_data(attachment_id)
    if not att:
        return jsonify({"error": "Attachment not found."}), 404

    data = att["data"]
    if att.get("encryption_key"):
        data = crypto_utils.decrypt_attachment(data, att["encryption_key"])

    return send_file(io.BytesIO(data), download_name=att["filename"],
                     mimetype=att["mimetype"], as_attachment=True)


# ── Routes: Search ───────────────────────────────────────────────────────────

@app.route("/api/search/<username>")
@_require_auth
def api_search(username: str):
    if username not in clients:
        return jsonify({"error": f"Unknown user '{username}'"}), 404
    err = _assert_own_user(username)
    if err:
        return err
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"emails": inboxes.get(username, [])})
    results = db.search_emails(username, q)
    return jsonify({"emails": results})


# ── Routes: Read ─────────────────────────────────────────────────────────────

@app.route("/api/read/<username>/<int:email_id>", methods=["POST"])
@_require_auth
def api_mark_read(username: str, email_id: int):
    if username not in clients:
        return jsonify({"error": f"Unknown user '{username}'"}), 404
    err = _assert_own_user(username)
    if err:
        return err
    db.mark_read(email_id)
    for em in inboxes.get(username, []):
        if em.get("id") == email_id:
            em["read"] = True
            break
    return jsonify({"ok": True})


# ── Routes: Sessions ─────────────────────────────────────────────────────────

@app.route("/api/sessions/<username>")
@_require_auth
def api_sessions(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    err = _assert_own_user(username)
    if err:
        return err
    return jsonify({"sessions": db.load_sessions(username)})


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def api_revoke_session(session_id: str):
    db.delete_session(session_id)
    return jsonify({"ok": True})


# ── Routes: Audit Log ────────────────────────────────────────────────────────

@app.route("/api/audit/<username>")
@_require_auth
def api_audit(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    err = _assert_own_user(username)
    if err:
        return err
    limit = request.args.get("limit", 100, type=int)
    return jsonify({"log": db.load_audit_log(username, limit)})


# ── Routes: Settings ─────────────────────────────────────────────────────────

@app.route("/api/settings/<username>")
@_require_auth
def api_get_settings(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    err = _assert_own_user(username)
    if err:
        return err
    return jsonify({"settings": db.get_settings(username)})


@app.route("/api/settings/<username>", methods=["POST"])
@_require_auth
def api_save_settings(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    err = _assert_own_user(username)
    if err:
        return err
    data = request.get_json(force=True)
    db.save_settings(username, **data)
    return jsonify({"ok": True})


# ── Routes: Keys ─────────────────────────────────────────────────────────────

@app.route("/api/keys/<username>")
@_require_auth
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
@_require_auth
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
@_require_auth
def api_verify_keys():
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
    encrypted_blob = None
    if password:
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        pw_hash = ph.hash(password)
        if config.ZERO_KNOWLEDGE_MODE:
            encrypted_blob = crypto_utils.encrypt_key_blob({
                "kyber_sk": c.kyber_sk,
                "dilithium_sk": c.dilithium_sk,
                "rsa_sk": c.rsa_sk or b"",
            }, password)

    db.save_user(username, c.kyber_pk, c.kyber_sk, c.dilithium_pk, c.dilithium_sk, pw_hash,
                 rsa_pk=c.rsa_pk, rsa_sk=c.rsa_sk, encrypted_key_blob=encrypted_blob)
    db.log_audit(username, "register", "User registered", _get_ip())
    metrics.inc("auth_register_total")

    # Auto-login: create a session and issue tokens so the frontend can
    # redirect straight to the dashboard without a second login round-trip.
    session["username"] = username
    sid = secrets.token_hex(16)
    session["session_id"] = sid
    db.save_session(sid, username, _get_ip(), request.user_agent.string)
    tokens = jwt_auth.create_token_pair(username)

    return jsonify({"ok": True, "user": _user_info(username), "steps": keygen["steps"], **tokens})


# ── Routes: Undo Send ────────────────────────────────────────────────────────

@app.route("/api/undo-send/<pending_id>", methods=["POST"])
def api_undo_send(pending_id: str):
    if pending_id in undo_queue:
        info = undo_queue.pop(pending_id)
        recipient = info.get("recipient", "")
        if recipient in mail_server.mailboxes and mail_server.mailboxes[recipient]:
            mail_server.mailboxes[recipient].pop()
        return jsonify({"ok": True, "message": "Send cancelled."})
    return jsonify({"error": "Undo window expired or invalid ID."}), 400


# ── Routes: Report Export ────────────────────────────────────────────────────

@app.route("/api/report/<username>")
@_require_auth
def api_report(username: str):
    if username not in clients:
        return jsonify({"error": "Unknown user"}), 404
    err = _assert_own_user(username)
    if err:
        return err
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

<div class="section"><h2>Features</h2>
<table><tr><th>Feature</th><th>Status</th></tr>
<tr><td>Zero-Knowledge Mode</td><td>{'Enabled' if config.ZERO_KNOWLEDGE_MODE else 'Disabled'}</td></tr>
<tr><td>Forward Secrecy</td><td>{'Enabled' if config.FORWARD_SECRECY else 'Disabled'}</td></tr>
<tr><td>Encrypted Attachments</td><td>Enabled</td></tr>
<tr><td>Email Threading</td><td>Enabled</td></tr>
<tr><td>Multi-Recipient</td><td>Enabled</td></tr></table></div>

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


# ── Routes: Metrics ──────────────────────────────────────────────────────────

@app.route("/metrics")
def prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    return Response(metrics.render_prometheus(), mimetype="text/plain")


@app.route("/api/metrics")
def api_metrics():
    """JSON metrics for the UI."""
    return jsonify(metrics.get_metrics())


# ── WebSocket Events ─────────────────────────────────────────────────────────

if socketio:
    @socketio.on("connect")
    def ws_connect():
        pass

    @socketio.on("join")
    def ws_join(data):
        username = data.get("username", "")
        if username in clients:
            join_room(username)
            logger.info("WebSocket: %s joined room", username)


# ── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  Schrödinger Mail — Quantum-Secure Email Client")
    print(f"  KEM : {crypto_utils.KEM_ALG}")
    print(f"  SIG : {crypto_utils.SIG_ALG}")
    print(f"  DEM : AES-256-GCM")
    print(f"  Users loaded: {', '.join(clients.keys())}")
    print(f"  Features: ZK={'on' if config.ZERO_KNOWLEDGE_MODE else 'off'}, "
          f"FS={'on' if config.FORWARD_SECRECY else 'off'}, "
          f"WS={'on' if socketio else 'off'}")
    print(f"  Debug: {config.DEBUG}")
    print(f"  Open http://127.0.0.1:{config.PORT} in your browser.\n")

    if socketio:
        socketio.run(app, host="0.0.0.0", debug=config.DEBUG, port=config.PORT, allow_unsafe_werkzeug=True)
    else:
        app.run(host="0.0.0.0", debug=config.DEBUG, port=config.PORT)
