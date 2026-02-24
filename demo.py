#!/usr/bin/env python3
"""
demo.py — Schrödinger Mail: End-to-End Simulation
==============================================================
This script runs a complete demonstration of the Signed KEM-DEM email system.

Scenario:
  1. A central server is created.
  2. Alice and Bob each generate post-quantum key pairs and register.
  3. Alice composes an email, signs it, encrypts it, and sends it to Bob.
  4. Bob fetches, decrypts, and verifies the email.
  5. A tamper-detection demo shows what happens when ciphertext is modified.

Run:
    pip install liboqs-python pycryptodome
    python demo.py
"""

from __future__ import annotations

import sys

# ── Project imports ──────────────────────────────────────────────────────────
from server import Server
from client import Client
import crypto_utils


# ── Pretty-print helpers ────────────────────────────────────────────────────

SEPARATOR = "=" * 72

def heading(title: str) -> None:
    """Print a section heading."""
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def subheading(title: str) -> None:
    """Print a sub-section heading."""
    print(f"\n--- {title} ---")


# ── Main simulation ─────────────────────────────────────────────────────────

def main() -> None:
    heading("QUANTUM-SECURE P2P EMAIL CLIENT — DEMO")
    print(f"  KEM algorithm : {crypto_utils.KEM_ALG}")
    print(f"  SIG algorithm : {crypto_utils.SIG_ALG}")
    print(f"  DEM algorithm : AES-256-GCM (pycryptodome)")

    # ==================================================================
    # PHASE 1 — Server Initialisation
    # ==================================================================
    heading("PHASE 1: Server Initialisation")
    server = Server()
    print("  Central key server created (in-memory).")

    # ==================================================================
    # PHASE 2 — User Registration
    # ==================================================================
    heading("PHASE 2: User Registration")

    subheading("Registering Alice")
    alice = Client("alice", server)
    print(f"  Kyber PK    : {len(alice.kyber_pk)} bytes")
    print(f"  Kyber SK    : {len(alice.kyber_sk)} bytes")
    print(f"  Dilithium PK: {len(alice.dilithium_pk)} bytes")
    print(f"  Dilithium SK: {len(alice.dilithium_sk)} bytes")
    print("  Alice registered successfully.")

    subheading("Registering Bob")
    bob = Client("bob", server)
    print(f"  Kyber PK    : {len(bob.kyber_pk)} bytes")
    print(f"  Kyber SK    : {len(bob.kyber_sk)} bytes")
    print(f"  Dilithium PK: {len(bob.dilithium_pk)} bytes")
    print(f"  Dilithium SK: {len(bob.dilithium_sk)} bytes")
    print("  Bob registered successfully.")

    # ==================================================================
    # PHASE 3 — Alice Sends a Quantum-Secure Email to Bob
    # ==================================================================
    heading("PHASE 3: Alice Sends an Email to Bob")
    email_subject = "Quantum Hello"
    email_body    = (
        "Hi Bob,\n\n"
        "This message is protected by post-quantum cryptography.\n"
        "It was signed with Dilithium3 and encrypted with Kyber768 + AES-256-GCM.\n\n"
        "Cheers,\nAlice"
    )

    print(f"  To      : bob")
    print(f"  Subject : {email_subject}")
    print(f"  Body    :\n")
    for line in email_body.split("\n"):
        print(f"    {line}")

    subheading("Sender Workflow Executing")
    package = alice.send_email(
        recipient = "bob",
        subject   = email_subject,
        body      = email_body,
    )

    print(f"  1. Fetched Bob's Kyber PK from server       ✓")
    print(f"  2. Signed message with Alice's Dilithium SK  ✓")
    print(f"  3. Built combined payload (sig + message)    ✓")
    print(f"  4. KEM encapsulated shared secret            ✓")
    print(f"     Encapsulated key : {len(package['encapsulated_key'])} bytes")
    print(f"  5. AES-256-GCM encrypted payload             ✓")
    print(f"     Ciphertext       : {len(package['ciphertext'])} bytes")
    print(f"     Nonce            : {len(package['nonce'])} bytes")
    print(f"     GCM Tag          : {len(package['tag'])} bytes")
    print(f"  6. Package sent to server for Bob            ✓")

    # ==================================================================
    # PHASE 4 — Bob Receives and Verifies the Email
    # ==================================================================
    heading("PHASE 4: Bob Receives and Verifies the Email")
    subheading("Receiver Workflow Executing")

    results = bob.receive_emails()

    for i, result in enumerate(results, 1):
        print(f"\n  Message #{i} from '{result['sender']}':")

        if result["verified"]:
            print(f"  1. KEM decapsulated shared secret            ✓")
            print(f"  2. AES-256-GCM decrypted successfully        ✓")
            print(f"  3. Payload split into signature + message    ✓")
            print(f"  4. Fetched sender's Dilithium PK from server ✓")
            print(f"  5. Signature VERIFIED                         ✓")
            print(f"\n  ── Decrypted & Verified Message ──")
            for line in result["plaintext"].split("\n"):
                print(f"    {line}")
        else:
            print(f"  ERROR: {result['error']}")

    # ==================================================================
    # PHASE 5 — Tamper Detection Demonstration
    # ==================================================================
    heading("PHASE 5: Tamper Detection Demonstration")
    print("  Simulating a man-in-the-middle attack by flipping a byte")
    print("  in the ciphertext before Bob tries to decrypt it.\n")

    # Alice sends another message
    package2 = alice.send_email(
        recipient = "bob",
        subject   = "Secret Plans",
        body      = "This message will be tampered with in transit!",
    )

    # ---- Tamper with the ciphertext while it sits on the server ----
    # Access Bob's mailbox directly (simulating an attacker with server access).
    tampered_messages = server.mailboxes["bob"]
    if tampered_messages:
        original_ct = bytearray(tampered_messages[0]["ciphertext"])
        # Flip one bit in the first byte of the ciphertext.
        original_ct[0] ^= 0xFF
        tampered_messages[0]["ciphertext"] = bytes(original_ct)
        print("  Ciphertext tampered: first byte XORed with 0xFF")

    subheading("Bob Attempts to Decrypt Tampered Message")
    results2 = bob.receive_emails()

    for i, result in enumerate(results2, 1):
        print(f"\n  Message #{i} from '{result['sender']}':")
        if result["verified"]:
            print(f"  Decrypted successfully (unexpected!):")
            print(f"    {result['plaintext']}")
        else:
            print(f"  REJECTED — {result['error']}")
            print(f"\n  The tampered message was correctly detected and rejected.")

    # ==================================================================
    # Summary
    # ==================================================================
    heading("DEMO COMPLETE")
    print("  This demonstration showed:")
    print("    • Post-quantum key generation (Kyber768 + Dilithium3)")
    print("    • Sign-then-Encrypt workflow (Signed KEM-DEM)")
    print("    • Successful send, decrypt, and signature verification")
    print("    • Tamper detection via AES-256-GCM authentication tag failure")
    print(f"\n{SEPARATOR}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n[FATAL] {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
