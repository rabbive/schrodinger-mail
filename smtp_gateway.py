#!/usr/bin/env python3
"""
smtp_gateway.py — SMTP/IMAP Gateway
=====================================
Bridges the quantum-secure email system with standard email infrastructure.
Outbound messages are encrypted with PQC, then sent over SMTP.
Inbound messages from IMAP are stored for PQC-enabled recipients.
"""

from __future__ import annotations

import email
import email.mime.multipart
import email.mime.text
import email.mime.base
import imaplib
import logging
import smtplib
from typing import Any, Dict, List, Optional

import config

logger = logging.getLogger(__name__)


class SMTPGateway:
    """Send encrypted email payloads over standard SMTP."""

    def __init__(
        self,
        host: str = "",
        port: int = 587,
        username: str = "",
        password: str = "",
        use_tls: bool = True,
    ) -> None:
        self.host = host or config.SMTP_HOST
        self.port = port or config.SMTP_PORT
        self.username = username or config.SMTP_USER
        self.password = password or config.SMTP_PASS
        self.use_tls = use_tls

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.username)

    def send(
        self,
        from_addr: str,
        to_addrs: List[str],
        subject: str,
        encrypted_payload: bytes,
        message_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
    ) -> bool:
        """
        Send an encrypted payload as an email attachment over SMTP.

        The message body indicates the email is PQC-encrypted.
        The actual encrypted data is attached as ``encrypted.bin``.
        """
        if not self.is_configured:
            logger.warning("SMTP gateway not configured, skipping send")
            return False

        msg = email.mime.multipart.MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = ", ".join(to_addrs)
        msg["Subject"] = f"[Schrödinger Mail] {subject}"
        if message_id:
            msg["Message-ID"] = f"<{message_id}@schrodinger-mail>"
        if in_reply_to:
            msg["In-Reply-To"] = f"<{in_reply_to}@schrodinger-mail>"

        body = (
            "This message is encrypted with post-quantum cryptography "
            "(CRYSTALS-Kyber768 + CRYSTALS-Dilithium3 + AES-256-GCM).\n\n"
            "To read this message, open it in Schrödinger Mail.\n"
            "The encrypted payload is attached as 'encrypted.bin'."
        )
        msg.attach(email.mime.text.MIMEText(body, "plain"))

        attachment = email.mime.base.MIMEBase("application", "octet-stream")
        attachment.set_payload(encrypted_payload)
        import email.encoders
        email.encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition", "attachment", filename="encrypted.bin",
        )
        msg.attach(attachment)

        try:
            if self.use_tls:
                server = smtplib.SMTP(self.host, self.port)
                server.ehlo()
                server.starttls()
            else:
                server = smtplib.SMTP(self.host, self.port)
            server.ehlo()
            if self.username and self.password:
                server.login(self.username, self.password)
            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.quit()
            logger.info("SMTP send successful to %s", to_addrs)
            return True
        except Exception:
            logger.exception("SMTP send failed")
            return False


class IMAPGateway:
    """Fetch encrypted emails from an IMAP mailbox."""

    def __init__(
        self,
        host: str = "",
        port: int = 993,
        username: str = "",
        password: str = "",
    ) -> None:
        self.host = host or config.IMAP_HOST
        self.port = port or config.IMAP_PORT
        self.username = username or config.SMTP_USER
        self.password = password or config.SMTP_PASS

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.username)

    def fetch_encrypted_messages(
        self, folder: str = "INBOX", mark_read: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Fetch unread messages that contain encrypted.bin attachments.

        Returns a list of dicts with keys:
            from, subject, message_id, in_reply_to, encrypted_payload
        """
        if not self.is_configured:
            logger.warning("IMAP gateway not configured")
            return []

        results: List[Dict[str, Any]] = []
        try:
            conn = imaplib.IMAP4_SSL(self.host, self.port)
            conn.login(self.username, self.password)
            conn.select(folder)
            _, message_numbers = conn.search(None, "UNSEEN")
            for num in message_numbers[0].split():
                _, data = conn.fetch(num, "(RFC822)")
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                encrypted_payload = None
                for part in msg.walk():
                    if part.get_filename() == "encrypted.bin":
                        encrypted_payload = part.get_payload(decode=True)
                        break

                if encrypted_payload:
                    results.append({
                        "from": msg.get("From", ""),
                        "subject": msg.get("Subject", "").replace("[Schrödinger Mail] ", ""),
                        "message_id": msg.get("Message-ID", ""),
                        "in_reply_to": msg.get("In-Reply-To", ""),
                        "encrypted_payload": encrypted_payload,
                    })
                    if mark_read:
                        conn.store(num, "+FLAGS", "\\Seen")

            conn.close()
            conn.logout()
            logger.info("IMAP fetch: found %d encrypted messages", len(results))
        except Exception:
            logger.exception("IMAP fetch failed")
        return results
