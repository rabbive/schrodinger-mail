"""Tests for database.py — SQLite CRUD operations, thread safety, and schema integrity."""

import threading

import pytest

import database as db


# ── Users ────────────────────────────────────────────────────────────────────

class TestUsers:
    def test_save_and_load_user(self):
        db.save_user("alice", b"pk1", b"sk1", b"pk2", b"sk2")
        users = db.load_users()
        assert len(users) == 1
        assert users[0]["username"] == "alice"
        assert users[0]["kyber_pk"] == b"pk1"
        assert users[0]["dilithium_sk"] == b"sk2"

    def test_user_exists(self):
        assert db.user_exists("alice") is False
        db.save_user("alice", b"pk", b"sk", b"pk", b"sk")
        assert db.user_exists("alice") is True

    def test_save_user_with_password(self):
        db.save_user("bob", b"pk", b"sk", b"pk", b"sk", password_hash="$argon2id$test")
        assert db.get_password_hash("bob") == "$argon2id$test"

    def test_update_password(self):
        db.save_user("charlie", b"pk", b"sk", b"pk", b"sk")
        assert db.get_password_hash("charlie") is None
        db.update_password("charlie", "$hash$new")
        assert db.get_password_hash("charlie") == "$hash$new"

    def test_password_hash_unknown_user(self):
        assert db.get_password_hash("unknown") is None

    def test_multiple_users(self):
        for name in ("alice", "bob", "charlie"):
            db.save_user(name, b"pk", b"sk", b"pk", b"sk")
        users = db.load_users()
        assert len(users) == 3


# ── Emails ───────────────────────────────────────────────────────────────────

class TestEmails:
    def test_save_and_load_email(self):
        eid = db.save_email("bob", "alice", "Hello", True, subject="Greetings")
        assert eid > 0
        emails = db.load_emails("bob")
        assert len(emails) == 1
        assert emails[0]["sender"] == "alice"
        assert emails[0]["subject"] == "Greetings"
        assert emails[0]["verified"] is True

    def test_email_defaults(self):
        db.save_email("bob", "alice", "Body", False)
        emails = db.load_emails("bob")
        assert emails[0]["folder"] == "inbox"
        assert emails[0]["read"] is False

    def test_move_email(self):
        eid = db.save_email("bob", "alice", "text", True)
        db.move_email(eid, "archive")
        emails = db.load_emails_by_folder("bob", "archive")
        assert len(emails) == 1

    def test_mark_read(self):
        eid = db.save_email("bob", "alice", "text", True)
        db.mark_read(eid)
        emails = db.load_emails("bob")
        assert emails[0]["read"] is True

    def test_delete_permanent(self):
        eid = db.save_email("bob", "alice", "text", True)
        db.delete_email_permanent(eid)
        assert len(db.load_emails("bob")) == 0

    def test_empty_trash(self):
        db.save_email("bob", "alice", "msg1", True, folder="trash")
        db.save_email("bob", "alice", "msg2", True, folder="trash")
        db.save_email("bob", "alice", "msg3", True, folder="inbox")
        count = db.empty_trash("bob")
        assert count == 2
        assert len(db.load_emails("bob")) == 1

    def test_search_emails(self):
        db.save_email("bob", "alice", "Meeting tomorrow", True, subject="Meeting")
        db.save_email("bob", "eve", "Party invite", True, subject="Party")
        results = db.search_emails("bob", "Meeting")
        assert len(results) == 1
        assert results[0]["subject"] == "Meeting"

    def test_search_case_insensitive(self):
        db.save_email("bob", "alice", "IMPORTANT data", True, subject="Important")
        results = db.search_emails("bob", "important")
        assert len(results) == 1

    def test_folder_counts(self):
        db.save_email("bob", "a", "x", True, folder="inbox")
        db.save_email("bob", "b", "y", True, folder="inbox")
        eid = db.save_email("bob", "c", "z", True, folder="sent")
        db.mark_read(eid)
        counts = db.get_folder_counts("bob")
        assert counts["inbox"]["total"] == 2
        assert counts["inbox"]["unread"] == 2
        assert counts["sent"]["total"] == 1
        assert counts["sent"]["unread"] == 0

    def test_load_emails_by_folder(self):
        db.save_email("bob", "a", "x", True, folder="inbox")
        db.save_email("bob", "b", "y", True, folder="sent")
        inbox = db.load_emails_by_folder("bob", "inbox")
        sent = db.load_emails_by_folder("bob", "sent")
        assert len(inbox) == 1
        assert len(sent) == 1


# ── Pending Messages ─────────────────────────────────────────────────────────

class TestPending:
    def test_save_and_load_pending(self):
        pid = db.save_pending("bob", "alice", b"enc", b"ct", b"nonce", b"tag")
        assert pid > 0
        pending = db.load_pending("bob")
        assert len(pending) == 1
        assert pending[0]["sender"] == "alice"
        assert pending[0]["encapsulated_key"] == b"enc"

    def test_delete_pending(self):
        db.save_pending("bob", "alice", b"e", b"c", b"n", b"t")
        db.delete_pending("bob")
        assert len(db.load_pending("bob")) == 0


# ── Drafts ───────────────────────────────────────────────────────────────────

class TestDrafts:
    def test_save_and_load_draft(self):
        did = db.save_draft("alice", "bob", "Subject", "Body text")
        assert did > 0
        drafts = db.load_drafts("alice")
        assert len(drafts) == 1
        assert drafts[0]["subject"] == "Subject"

    def test_update_draft(self):
        did = db.save_draft("alice", "bob", "Draft1", "Body1")
        db.save_draft("alice", "bob", "Updated", "New body", draft_id=did)
        drafts = db.load_drafts("alice")
        assert len(drafts) == 1
        assert drafts[0]["subject"] == "Updated"

    def test_delete_draft(self):
        did = db.save_draft("alice", "bob", "X", "Y")
        db.delete_draft(did, "alice")
        assert len(db.load_drafts("alice")) == 0

    def test_draft_isolation(self):
        db.save_draft("alice", "bob", "A", "B")
        db.save_draft("charlie", "bob", "C", "D")
        assert len(db.load_drafts("alice")) == 1
        assert len(db.load_drafts("charlie")) == 1


# ── Contacts ─────────────────────────────────────────────────────────────────

class TestContacts:
    def test_save_and_load_contact(self):
        cid = db.save_contact("alice", "Bob", "bob", kyber_fp="abc", dilithium_fp="def")
        assert cid > 0
        contacts = db.load_contacts("alice")
        assert len(contacts) == 1
        assert contacts[0]["name"] == "Bob"
        assert contacts[0]["kyber_fingerprint"] == "abc"

    def test_delete_contact(self):
        cid = db.save_contact("alice", "Bob")
        db.delete_contact(cid, "alice")
        assert len(db.load_contacts("alice")) == 0

    def test_verify_contact(self):
        cid = db.save_contact("alice", "Bob")
        db.update_contact_verified(cid, True)
        contacts = db.load_contacts("alice")
        assert contacts[0]["verified"] is True


# ── Attachments ──────────────────────────────────────────────────────────────

class TestAttachments:
    def test_save_and_load_attachment(self):
        eid = db.save_email("bob", "alice", "text", True)
        aid = db.save_attachment(eid, "doc.pdf", "application/pdf", b"PDF_DATA")
        assert aid > 0
        atts = db.load_attachments(eid)
        assert len(atts) == 1
        assert atts[0]["filename"] == "doc.pdf"

    def test_get_attachment_data(self):
        eid = db.save_email("bob", "alice", "text", True)
        aid = db.save_attachment(eid, "f.txt", "text/plain", b"content")
        data = db.get_attachment_data(aid)
        assert data is not None
        assert data["data"] == b"content"
        assert data["filename"] == "f.txt"

    def test_missing_attachment(self):
        assert db.get_attachment_data(99999) is None


# ── Sessions ─────────────────────────────────────────────────────────────────

class TestSessions:
    def test_save_and_load_session(self):
        db.save_session("sid1", "alice", "127.0.0.1", "Firefox")
        sessions = db.load_sessions("alice")
        assert len(sessions) == 1
        assert sessions[0]["ip_address"] == "127.0.0.1"

    def test_delete_session(self):
        db.save_session("sid2", "alice")
        db.delete_session("sid2")
        assert len(db.load_sessions("alice")) == 0

    def test_session_exists(self):
        db.save_session("sid3", "bob")
        assert db.session_exists("sid3") == "bob"
        assert db.session_exists("nonexistent") is None


# ── Audit Log ────────────────────────────────────────────────────────────────

class TestAuditLog:
    def test_log_and_load(self):
        db.log_audit("alice", "login", "Logged in", "10.0.0.1")
        log = db.load_audit_log("alice")
        assert len(log) == 1
        assert log[0]["action"] == "login"
        assert log[0]["ip_address"] == "10.0.0.1"

    def test_log_limit(self):
        for i in range(5):
            db.log_audit("alice", f"action_{i}", f"detail_{i}")
        log = db.load_audit_log("alice", limit=3)
        assert len(log) == 3

    def test_log_isolation(self):
        db.log_audit("alice", "a1")
        db.log_audit("bob", "b1")
        assert len(db.load_audit_log("alice")) == 1
        assert len(db.load_audit_log("bob")) == 1


# ── Seen IDs (Replay Protection) ────────────────────────────────────────────

class TestSeenIds:
    def test_save_and_load(self):
        db.save_seen_id("alice", "msg-001")
        db.save_seen_id("alice", "msg-002")
        ids = db.load_seen_ids("alice")
        assert ids == {"msg-001", "msg-002"}

    def test_duplicate_ignored(self):
        db.save_seen_id("alice", "msg-001")
        db.save_seen_id("alice", "msg-001")  # no error
        ids = db.load_seen_ids("alice")
        assert len(ids) == 1

    def test_user_isolation(self):
        db.save_seen_id("alice", "msg-001")
        db.save_seen_id("bob", "msg-002")
        assert db.load_seen_ids("alice") == {"msg-001"}
        assert db.load_seen_ids("bob") == {"msg-002"}


# ── User Settings ────────────────────────────────────────────────────────────

class TestSettings:
    def test_default_settings(self):
        settings = db.get_settings("unknown_user")
        assert settings["theme"] == "dark"
        assert settings["signature"] == ""
        assert settings["shortcuts"] is True

    def test_save_and_get_settings(self):
        db.save_settings("alice", signature="-- Alice")
        settings = db.get_settings("alice")
        assert settings["signature"] == "-- Alice"

    def test_update_settings(self):
        db.save_settings("alice", theme="light")
        db.save_settings("alice", theme="dark")
        assert db.get_settings("alice")["theme"] == "dark"


# ── Thread Safety ────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_writes(self):
        errors = []

        def writer(username):
            try:
                db.save_user(username, b"pk", b"sk", b"pk", b"sk")
                db.log_audit(username, "test")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=writer, args=(f"user{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        users = db.load_users()
        assert len(users) == 10
