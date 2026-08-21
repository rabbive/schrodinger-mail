#!/usr/bin/env python3
"""
models.py — SQLAlchemy ORM Models
===================================
Defines all database models for Schrödinger Mail.
Supports both SQLite (development) and PostgreSQL (production).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary,
    String, Text, UniqueConstraint, create_engine, event,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

import config


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    username = Column(String(32), primary_key=True)
    password_hash = Column(Text, nullable=True)
    kyber_pk = Column(LargeBinary, nullable=False)
    kyber_sk = Column(LargeBinary, nullable=False)
    dilithium_pk = Column(LargeBinary, nullable=False)
    dilithium_sk = Column(LargeBinary, nullable=False)
    rsa_pk = Column(LargeBinary, nullable=True)
    rsa_sk = Column(LargeBinary, nullable=True)
    encrypted_key_blob = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    emails = relationship("Email", back_populates="recipient_user", foreign_keys="Email.recipient")
    drafts = relationship("Draft", back_populates="owner_user")
    contacts = relationship("Contact", back_populates="owner_user")
    settings = relationship("UserSettings", back_populates="user", uselist=False)


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipient = Column(String(32), ForeignKey("users.username"), nullable=False, index=True)
    sender = Column(String(32), nullable=False)
    subject = Column(Text, default="")
    plaintext = Column(Text, nullable=True)
    verified = Column(Boolean, default=False)
    error = Column(Text, nullable=True)
    read = Column(Boolean, default=False)
    folder = Column(String(20), default="inbox", index=True)
    enc_subject = Column(Boolean, default=False)
    thread_id = Column(String(64), nullable=True, index=True)
    in_reply_to = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    recipient_user = relationship("User", back_populates="emails", foreign_keys=[recipient])
    attachments = relationship("Attachment", back_populates="email", cascade="all, delete-orphan")


class Pending(Base):
    __tablename__ = "pending"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipient = Column(String(32), nullable=False, index=True)
    sender = Column(String(32), nullable=False)
    encapsulated_key = Column(LargeBinary, nullable=False)
    ciphertext = Column(LargeBinary, nullable=False)
    nonce = Column(LargeBinary, nullable=False)
    tag = Column(LargeBinary, nullable=False)


class Draft(Base):
    __tablename__ = "drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner = Column(String(32), ForeignKey("users.username"), nullable=False, index=True)
    recipient = Column(Text, default="")
    subject = Column(Text, default="")
    body = Column(Text, default="")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    owner_user = relationship("User", back_populates="drafts")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner = Column(String(32), ForeignKey("users.username"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    username = Column(String(32), default="")
    kyber_fingerprint = Column(String(200), default="")
    dilithium_fingerprint = Column(String(200), default="")
    verified = Column(Boolean, default=False)
    notes = Column(Text, default="")
    # Optional P2P fields for direct LAN delivery
    peer_address = Column(String(255), default="")  # e.g. "192.168.1.10:6001"
    device_label = Column(String(100), default="")

    owner_user = relationship("User", back_populates="contacts")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=True)
    filename = Column(String(255), nullable=False)
    mimetype = Column(String(100), default="application/octet-stream")
    size_bytes = Column(Integer, default=0)
    data = Column(LargeBinary, nullable=False)
    encryption_key = Column(LargeBinary, nullable=True)

    email = relationship("Email", back_populates="attachments")


class SessionRecord(Base):
    __tablename__ = "sessions"

    session_id = Column(String(64), primary_key=True)
    username = Column(String(32), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    last_active = Column(DateTime, nullable=False)
    ip_address = Column(String(45), default="")
    user_agent = Column(Text, default="")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    details = Column(Text, default="")
    ip_address = Column(String(45), default="")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SeenId(Base):
    __tablename__ = "seen_ids"

    username = Column(String(32), primary_key=True)
    message_id = Column(String(64), primary_key=True)


class UserSettings(Base):
    __tablename__ = "user_settings"

    username = Column(String(32), ForeignKey("users.username"), primary_key=True)
    signature = Column(Text, default="")
    theme = Column(String(10), default="dark")
    shortcuts = Column(Boolean, default=True)
    notifications = Column(Boolean, default=True)

    user = relationship("User", back_populates="settings")


class RatchetState(Base):
    """Stores forward-secrecy ratchet state between two users."""
    __tablename__ = "ratchet_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_a = Column(String(32), nullable=False, index=True)
    user_b = Column(String(32), nullable=False, index=True)
    chain_key = Column(LargeBinary, nullable=False)
    step = Column(Integer, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_a", "user_b", name="uq_ratchet_pair"),
    )


# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

def get_engine(url: Optional[str] = None):
    """Create a SQLAlchemy engine from a URL or config."""
    if url is None:
        url = getattr(config, "DATABASE_URL", None) or f"sqlite:///{config.DB_PATH}"
    connect_args = {}
    engine_options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        # Small pool fits Heroku's entry-level Postgres connection limits.
        engine_options.update(pool_size=5, max_overflow=2, pool_recycle=300)
    engine = create_engine(url, connect_args=connect_args, **engine_options)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def create_all(engine):
    """Create all tables."""
    Base.metadata.create_all(engine)


def get_session_factory(engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)
