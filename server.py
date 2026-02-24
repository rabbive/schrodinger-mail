#!/usr/bin/env python3
"""
server.py — Simulated Central Key & Mail Server
=================================================
Provides an in-memory mock of a mail server that:

1. **Stores public keys** — Each user registers their Kyber (KEM) and
   Dilithium (signature) public keys so that any peer can look them up.
2. **Relays encrypted message packages** — A simple per-user mailbox holds
   encrypted packages until the recipient fetches them.

This is intentionally simple (a Python dict acting as a database) so the
focus stays on the cryptographic workflow rather than networking.

Note
----
``demo.py`` accesses ``server.mailboxes`` directly to simulate a
man-in-the-middle tamper attack.  The attribute must therefore remain a
plain ``dict`` rather than being hidden behind a private name.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List


class Server:
    """In-memory key directory and mailbox relay."""

    def __init__(self) -> None:
        # ── Public-key directory ──────────────────────────────────────
        # Maps username -> {"kyber_pk": bytes, "dilithium_pk": bytes}
        self.public_keys: Dict[str, Dict[str, bytes]] = {}

        # ── Per-user mailboxes ────────────────────────────────────────
        # Maps username -> list of encrypted message packages (dicts).
        # Each package contains: encapsulated_key, ciphertext, nonce,
        # tag, and sender.
        self.mailboxes: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    # ------------------------------------------------------------------
    # User registration
    # ------------------------------------------------------------------

    def register_user(
        self,
        username: str,
        kyber_pk: bytes,
        dilithium_pk: bytes,
    ) -> None:
        """
        Register a user's public keys on the server.

        Parameters
        ----------
        username : str
            Unique user identifier (e.g. ``"alice"``).
        kyber_pk : bytes
            Kyber768 public key for key encapsulation.
        dilithium_pk : bytes
            Dilithium3 / ML-DSA-65 public key for signature verification.

        Raises
        ------
        ValueError
            If *username* is already registered.
        """
        if username in self.public_keys:
            raise ValueError(f"User '{username}' is already registered.")

        self.public_keys[username] = {
            "kyber_pk": kyber_pk,
            "dilithium_pk": dilithium_pk,
        }

    # ------------------------------------------------------------------
    # Public-key look-ups
    # ------------------------------------------------------------------

    def get_public_keys(self, username: str) -> Dict[str, bytes]:
        """
        Retrieve both public keys for *username*.

        Returns
        -------
        dict
            ``{"kyber_pk": bytes, "dilithium_pk": bytes}``

        Raises
        ------
        KeyError
            If the user is not registered.
        """
        if username not in self.public_keys:
            raise KeyError(f"User '{username}' is not registered on this server.")
        return self.public_keys[username]

    # ------------------------------------------------------------------
    # Message relay
    # ------------------------------------------------------------------

    def send_message(
        self,
        sender: str,
        recipient: str,
        package: Dict[str, Any],
    ) -> None:
        """
        Deliver an encrypted message package to *recipient*'s mailbox.

        The *sender* field is attached to the package so the recipient
        knows whose Dilithium key to fetch for verification.

        Parameters
        ----------
        sender : str
            Username of the message author.
        recipient : str
            Username of the intended recipient.
        package : dict
            Must contain at minimum: ``encapsulated_key``, ``ciphertext``,
            ``nonce``, and ``tag``.

        Raises
        ------
        KeyError
            If *recipient* is not registered.
        """
        if recipient not in self.public_keys:
            raise KeyError(
                f"Cannot deliver message: recipient '{recipient}' is not registered."
            )

        # Attach the sender identity so the receiver can look up the
        # sender's Dilithium public key for signature verification.
        package_with_sender = {**package, "sender": sender}
        self.mailboxes[recipient].append(package_with_sender)

    def fetch_messages(self, username: str) -> List[Dict[str, Any]]:
        """
        Retrieve and **clear** all messages from *username*'s mailbox.

        Returns
        -------
        list[dict]
            A (possibly empty) list of encrypted message packages.
        """
        messages = list(self.mailboxes[username])
        self.mailboxes[username].clear()
        return messages
