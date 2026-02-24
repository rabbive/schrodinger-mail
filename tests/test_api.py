"""Tests for app.py — Flask API endpoints, authentication, send/receive, and attack demos."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db


@pytest.fixture()
def app_client(monkeypatch, tmp_path):
    """Create a fresh Flask test client with an isolated database."""
    db_path = tmp_path / "test_app.db"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionFactory", None)

    import config as cfg
    monkeypatch.setattr(cfg, "DB_PATH", db_path)
    monkeypatch.setattr(cfg, "DATABASE_URL", db_url)

    import server as srv
    import app as app_module

    # Reset global state
    app_module.mail_server = srv.Server()
    app_module.clients.clear()
    app_module.inboxes.clear()

    # Re-initialise with fresh DB
    db.init_db()
    for name in ("alice", "bob"):
        from client import Client
        c = Client(name, app_module.mail_server)
        app_module.clients[name] = c
        app_module.inboxes[name] = []
        db.save_user(name, c.kyber_pk, c.kyber_sk, c.dilithium_pk, c.dilithium_sk)

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        yield client


def _get_csrf(client):
    """Fetch a CSRF token by hitting the auth status endpoint."""
    resp = client.get("/api/auth/status")
    return resp.get_json().get("csrf_token", "")


def _post_json(client, url, data=None, csrf=None):
    headers = {}
    if csrf:
        headers["X-CSRF-Token"] = csrf
    return client.post(url, data=json.dumps(data or {}),
                       content_type="application/json", headers=headers)


# ── State & Health ───────────────────────────────────────────────────────────

class TestState:
    def test_get_state(self, app_client):
        resp = app_client.get("/api/state")
        data = resp.get_json()
        assert resp.status_code == 200
        assert "alice" in data["users"]
        assert "bob" in data["users"]
        assert "kem_algorithm" in data

    def test_index_renders(self, app_client):
        resp = app_client.get("/")
        assert resp.status_code == 200


# ── Send & Receive ───────────────────────────────────────────────────────────

class TestSendReceive:
    def test_send_email(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/send", {
            "sender": "alice", "recipient": "bob",
            "subject": "Hello", "body": "World",
        }, csrf)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["ok"] is True
        assert "steps" in data

    def test_send_to_unknown_user(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/send", {
            "sender": "alice", "recipient": "unknown",
            "subject": "X", "body": "Y",
        }, csrf)
        assert resp.status_code == 404

    def test_send_empty_body(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/send", {
            "sender": "alice", "recipient": "bob",
            "subject": "Hi", "body": "",
        }, csrf)
        assert resp.status_code == 400

    def test_receive_email(self, app_client):
        csrf = _get_csrf(app_client)
        _post_json(app_client, "/api/send", {
            "sender": "alice", "recipient": "bob",
            "subject": "Test", "body": "Content",
        }, csrf)
        resp = _post_json(app_client, "/api/receive/bob", csrf=csrf)
        data = resp.get_json()
        assert resp.status_code == 200
        assert len(data["results"]) == 1
        assert data["results"][0]["verified"] is True
        assert "Test" in data["results"][0].get("plaintext", "")

    def test_receive_no_messages(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/receive/alice", csrf=csrf)
        data = resp.get_json()
        assert data["ok"] is True
        assert len(data["results"]) == 0

    def test_send_hybrid_level3(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/send", {
            "sender": "alice", "recipient": "bob",
            "subject": "Hybrid", "body": "Defense-in-depth test",
            "security_level": 3,
        }, csrf)
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["ok"] is True
        assert data.get("security_level") == 3


# ── Attack Demos ─────────────────────────────────────────────────────────────

class TestAttackDemos:
    def test_tamper_detection(self, app_client):
        csrf = _get_csrf(app_client)
        _post_json(app_client, "/api/send", {
            "sender": "alice", "recipient": "bob",
            "subject": "Tamper Test", "body": "Original",
        }, csrf)
        resp = _post_json(app_client, "/api/tamper/bob", csrf=csrf)
        assert resp.status_code == 200

        resp = _post_json(app_client, "/api/receive/bob", csrf=csrf)
        results = resp.get_json()["results"]
        assert len(results) == 1
        assert results[0]["verified"] is False

    def test_tamper_no_pending(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/tamper/bob", csrf=csrf)
        assert resp.status_code == 400

    def test_forged_signature(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/send-forged", {
            "sender": "alice", "recipient": "bob",
            "subject": "Forged", "body": "Fake",
        }, csrf)
        assert resp.status_code == 200

        resp = _post_json(app_client, "/api/receive/bob", csrf=csrf)
        results = resp.get_json()["results"]
        assert len(results) == 1
        assert results[0]["verified"] is False

    def test_replay_detection(self, app_client):
        csrf = _get_csrf(app_client)
        _post_json(app_client, "/api/send", {
            "sender": "alice", "recipient": "bob",
            "subject": "Replay", "body": "Original",
        }, csrf)
        _post_json(app_client, "/api/replay/bob", csrf=csrf)

        resp = _post_json(app_client, "/api/receive/bob", csrf=csrf)
        results = resp.get_json()["results"]
        assert len(results) == 2
        verified_count = sum(1 for r in results if r["verified"])
        failed_count = sum(1 for r in results if not r["verified"])
        assert verified_count == 1
        assert failed_count == 1


# ── Folders ──────────────────────────────────────────────────────────────────

class TestFolders:
    def test_get_folders(self, app_client):
        resp = app_client.get("/api/folders/alice")
        data = resp.get_json()
        assert resp.status_code == 200
        names = [f["name"] for f in data["folders"]]
        assert "inbox" in names
        assert "sent" in names
        assert "trash" in names

    def test_move_and_delete(self, app_client):
        csrf = _get_csrf(app_client)
        _post_json(app_client, "/api/send", {
            "sender": "alice", "recipient": "bob",
            "subject": "Move", "body": "Me",
        }, csrf)
        _post_json(app_client, "/api/receive/bob", csrf=csrf)

        emails = app_client.get("/api/emails/bob/inbox").get_json()["emails"]
        assert len(emails) >= 1
        eid = emails[0]["id"]

        _post_json(app_client, f"/api/move/bob/{eid}", {"folder": "archive"}, csrf)
        archived = app_client.get("/api/emails/bob/archive").get_json()["emails"]
        assert any(e["id"] == eid for e in archived)


# ── Search ───────────────────────────────────────────────────────────────────

class TestSearch:
    def test_search(self, app_client):
        csrf = _get_csrf(app_client)
        _post_json(app_client, "/api/send", {
            "sender": "alice", "recipient": "bob",
            "subject": "Quantum Meeting", "body": "Discuss Kyber",
        }, csrf)
        _post_json(app_client, "/api/receive/bob", csrf=csrf)

        resp = app_client.get("/api/search/bob?q=Quantum")
        data = resp.get_json()
        assert len(data["emails"]) >= 1


# ── Registration ─────────────────────────────────────────────────────────────

class TestRegistration:
    def test_register_new_user(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/register", {
            "username": "charlie", "password": "pass1234",
        }, csrf)
        data = resp.get_json()
        assert data["ok"] is True
        assert data["user"]["username"] == "charlie"

    def test_register_duplicate(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/register", {"username": "alice"}, csrf)
        assert resp.status_code == 409

    def test_register_invalid_username(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/register", {"username": "!@#$"}, csrf)
        assert resp.status_code == 400


# ── Auth ─────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_login_without_password(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/auth/login", {"username": "alice"}, csrf)
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True

    def test_auth_status(self, app_client):
        resp = app_client.get("/api/auth/status")
        data = resp.get_json()
        assert "auth_enabled" in data
        assert "csrf_token" in data

    def test_set_password(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/auth/set-password", {
            "username": "alice", "password": "secure123",
        }, csrf)
        assert resp.status_code == 200

    def test_logout(self, app_client):
        csrf = _get_csrf(app_client)
        _post_json(app_client, "/api/auth/login", {"username": "alice"}, csrf)
        resp = _post_json(app_client, "/api/auth/logout", csrf=csrf)
        assert resp.get_json()["ok"] is True


# ── Keys ─────────────────────────────────────────────────────────────────────

class TestKeys:
    def test_get_keys(self, app_client):
        resp = app_client.get("/api/keys/alice")
        data = resp.get_json()
        assert "kyber_pk_fingerprint" in data
        assert "dilithium_pk_fingerprint" in data

    def test_export_key(self, app_client):
        resp = app_client.get("/api/keys/export/alice/kyber_pk")
        assert resp.status_code == 200
        assert len(resp.data) > 0

    def test_verify_keys(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/keys/verify", {
            "user_a": "alice", "user_b": "bob",
        }, csrf)
        data = resp.get_json()
        assert "user_a" in data
        assert "user_b" in data
        assert data["user_a"]["kyber_fingerprint"] != data["user_b"]["kyber_fingerprint"]


# ── Benchmarks ───────────────────────────────────────────────────────────────

class TestBenchmarksAPI:
    def test_benchmarks_endpoint(self, app_client):
        resp = app_client.get("/api/benchmarks")
        data = resp.get_json()
        assert "benchmarks" in data
        assert len(data["benchmarks"]) > 0


# ── Drafts API ───────────────────────────────────────────────────────────────

class TestDraftsAPI:
    def test_save_and_load_draft(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/draft/alice", {
            "recipient": "bob", "subject": "Draft", "body": "WIP",
        }, csrf)
        assert resp.get_json()["ok"] is True

        resp = app_client.get("/api/drafts/alice")
        drafts = resp.get_json()["drafts"]
        assert len(drafts) == 1
        assert drafts[0]["subject"] == "Draft"

    def test_delete_draft(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/draft/alice", {
            "subject": "Temp", "body": "Delete me",
        }, csrf)
        draft_id = resp.get_json()["draft_id"]

        app_client.delete(f"/api/draft/alice/{draft_id}")
        assert len(app_client.get("/api/drafts/alice").get_json()["drafts"]) == 0


# ── Contacts API ─────────────────────────────────────────────────────────────

class TestContactsAPI:
    def test_add_and_list_contact(self, app_client):
        csrf = _get_csrf(app_client)
        resp = _post_json(app_client, "/api/contacts/alice", {
            "name": "Bob", "username": "bob",
        }, csrf)
        assert resp.get_json()["ok"] is True

        contacts = app_client.get("/api/contacts/alice").get_json()["contacts"]
        assert len(contacts) == 1
        assert contacts[0]["name"] == "Bob"


# ── Audit Log API ───────────────────────────────────────────────────────────

class TestAuditLogAPI:
    def test_audit_log(self, app_client):
        csrf = _get_csrf(app_client)
        _post_json(app_client, "/api/send", {
            "sender": "alice", "recipient": "bob",
            "subject": "Audit", "body": "Test",
        }, csrf)
        resp = app_client.get("/api/audit/alice")
        log = resp.get_json()["log"]
        assert len(log) >= 1
        assert any("send" in entry["action"] for entry in log)


# ── Security Report ──────────────────────────────────────────────────────────

class TestReport:
    def test_download_report(self, app_client):
        resp = app_client.get("/api/report/alice")
        assert resp.status_code == 200
        assert b"Security Report" in resp.data
