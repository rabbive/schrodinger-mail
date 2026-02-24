"""Initial schema with all tables.

Revision ID: 001
Revises:
Create Date: 2026-02-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("username", sa.String(32), primary_key=True),
        sa.Column("password_hash", sa.Text, nullable=True),
        sa.Column("kyber_pk", sa.LargeBinary, nullable=False),
        sa.Column("kyber_sk", sa.LargeBinary, nullable=False),
        sa.Column("dilithium_pk", sa.LargeBinary, nullable=False),
        sa.Column("dilithium_sk", sa.LargeBinary, nullable=False),
        sa.Column("rsa_pk", sa.LargeBinary, nullable=True),
        sa.Column("rsa_sk", sa.LargeBinary, nullable=True),
        sa.Column("encrypted_key_blob", sa.LargeBinary, nullable=True),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "emails",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("recipient", sa.String(32), sa.ForeignKey("users.username"), nullable=False),
        sa.Column("sender", sa.String(32), nullable=False),
        sa.Column("subject", sa.Text, default=""),
        sa.Column("plaintext", sa.Text, nullable=True),
        sa.Column("verified", sa.Boolean, default=False),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("read", sa.Boolean, default=False),
        sa.Column("folder", sa.String(20), default="inbox"),
        sa.Column("enc_subject", sa.Boolean, default=False),
        sa.Column("thread_id", sa.String(64), nullable=True),
        sa.Column("in_reply_to", sa.String(64), nullable=True),
        sa.Column("timestamp", sa.DateTime),
    )
    op.create_index("ix_emails_recipient", "emails", ["recipient"])
    op.create_index("ix_emails_folder", "emails", ["folder"])
    op.create_index("ix_emails_thread_id", "emails", ["thread_id"])

    op.create_table(
        "pending",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("recipient", sa.String(32), nullable=False),
        sa.Column("sender", sa.String(32), nullable=False),
        sa.Column("encapsulated_key", sa.LargeBinary, nullable=False),
        sa.Column("ciphertext", sa.LargeBinary, nullable=False),
        sa.Column("nonce", sa.LargeBinary, nullable=False),
        sa.Column("tag", sa.LargeBinary, nullable=False),
    )
    op.create_index("ix_pending_recipient", "pending", ["recipient"])

    op.create_table(
        "drafts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("owner", sa.String(32), sa.ForeignKey("users.username"), nullable=False),
        sa.Column("recipient", sa.Text, default=""),
        sa.Column("subject", sa.Text, default=""),
        sa.Column("body", sa.Text, default=""),
        sa.Column("updated_at", sa.DateTime),
    )
    op.create_index("ix_drafts_owner", "drafts", ["owner"])

    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("owner", sa.String(32), sa.ForeignKey("users.username"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("username", sa.String(32), default=""),
        sa.Column("kyber_fingerprint", sa.String(200), default=""),
        sa.Column("dilithium_fingerprint", sa.String(200), default=""),
        sa.Column("verified", sa.Boolean, default=False),
        sa.Column("notes", sa.Text, default=""),
    )
    op.create_index("ix_contacts_owner", "contacts", ["owner"])

    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("email_id", sa.Integer, sa.ForeignKey("emails.id", ondelete="CASCADE"), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mimetype", sa.String(100), default="application/octet-stream"),
        sa.Column("size_bytes", sa.Integer, default=0),
        sa.Column("data", sa.LargeBinary, nullable=False),
        sa.Column("encryption_key", sa.LargeBinary, nullable=True),
    )

    op.create_table(
        "sessions",
        sa.Column("session_id", sa.String(64), primary_key=True),
        sa.Column("username", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("last_active", sa.DateTime, nullable=False),
        sa.Column("ip_address", sa.String(45), default=""),
        sa.Column("user_agent", sa.Text, default=""),
    )
    op.create_index("ix_sessions_username", "sessions", ["username"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(32), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("details", sa.Text, default=""),
        sa.Column("ip_address", sa.String(45), default=""),
        sa.Column("timestamp", sa.DateTime),
    )
    op.create_index("ix_audit_log_username", "audit_log", ["username"])

    op.create_table(
        "seen_ids",
        sa.Column("username", sa.String(32), primary_key=True),
        sa.Column("message_id", sa.String(64), primary_key=True),
    )

    op.create_table(
        "user_settings",
        sa.Column("username", sa.String(32), sa.ForeignKey("users.username"), primary_key=True),
        sa.Column("signature", sa.Text, default=""),
        sa.Column("theme", sa.String(10), default="dark"),
        sa.Column("shortcuts", sa.Boolean, default=True),
        sa.Column("notifications", sa.Boolean, default=True),
    )

    op.create_table(
        "ratchet_states",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_a", sa.String(32), nullable=False),
        sa.Column("user_b", sa.String(32), nullable=False),
        sa.Column("chain_key", sa.LargeBinary, nullable=False),
        sa.Column("step", sa.Integer, default=0),
        sa.Column("updated_at", sa.DateTime),
        sa.UniqueConstraint("user_a", "user_b", name="uq_ratchet_pair"),
    )
    op.create_index("ix_ratchet_states_user_a", "ratchet_states", ["user_a"])
    op.create_index("ix_ratchet_states_user_b", "ratchet_states", ["user_b"])


def downgrade() -> None:
    op.drop_table("ratchet_states")
    op.drop_table("user_settings")
    op.drop_table("seen_ids")
    op.drop_table("audit_log")
    op.drop_table("sessions")
    op.drop_table("attachments")
    op.drop_table("contacts")
    op.drop_table("drafts")
    op.drop_table("pending")
    op.drop_table("emails")
    op.drop_table("users")
