#!/usr/bin/env python3
"""
client.py — Schrödinger Mail Client
=========================================
Implements the Sender and Receiver workflows of the Signed KEM-DEM architecture
with support for reply/forward, encrypted subjects, password-protected messages,
and persistent replay detection.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import crypto_utils
from server import Server


class Client:
    """A single user in the quantum-secure email system."""

    def __init__(self, username: str, server: Server) -> None:
        self.username = username
        self.server = server
        self.kyber_pk, self.kyber_sk = crypto_utils.generate_kem_keypair()
        self.dilithium_pk, self.dilithium_sk = crypto_utils.generate_sig_keypair()
        self.rsa_pk, self.rsa_sk = crypto_utils.generate_rsa_keypair()
        self.server.register_user(
            username=self.username,
            kyber_pk=self.kyber_pk,
            dilithium_pk=self.dilithium_pk,
        )
        self.seen_message_ids: Set[str] = set()

    @classmethod
    def from_keys(
        cls, username: str, server: Server,
        kyber_pk: bytes, kyber_sk: bytes,
        dilithium_pk: bytes, dilithium_sk: bytes,
        seen_ids: Optional[Set[str]] = None,
        rsa_pk: Optional[bytes] = None,
        rsa_sk: Optional[bytes] = None,
    ) -> "Client":
        """Restore a client from pre-existing keys (loaded from DB)."""
        obj = object.__new__(cls)
        obj.username = username
        obj.server = server
        obj.kyber_pk = kyber_pk
        obj.kyber_sk = kyber_sk
        obj.dilithium_pk = dilithium_pk
        obj.dilithium_sk = dilithium_sk
        obj.seen_message_ids = seen_ids or set()
        if rsa_pk and rsa_sk:
            obj.rsa_pk = rsa_pk
            obj.rsa_sk = rsa_sk
        else:
            obj.rsa_pk, obj.rsa_sk = crypto_utils.generate_rsa_keypair()
        if username not in server.public_keys:
            server.register_user(username=username, kyber_pk=kyber_pk, dilithium_pk=dilithium_pk)
        return obj

    @staticmethod
    def generate_keys_with_log() -> Dict[str, Any]:
        """Generate all key pairs with step-by-step logs for the UI."""
        steps: List[Dict[str, Any]] = []
        kyber_pk, kyber_sk = crypto_utils.generate_kem_keypair()
        steps.append({
            "step": 1, "title": "Generate Kyber768 Key Pair (KEM)",
            "description": f"Generated Kyber768 keypair: public key = {len(kyber_pk)} bytes, secret key = {len(kyber_sk)} bytes.",
            "details": {"algorithm": crypto_utils.KEM_ALG, "public_key_bytes": len(kyber_pk),
                        "secret_key_bytes": len(kyber_sk), "pk_preview": kyber_pk[:16].hex() + "..."},
            "status": "success",
        })
        dilithium_pk, dilithium_sk = crypto_utils.generate_sig_keypair()
        steps.append({
            "step": 2, "title": "Generate Dilithium3 Key Pair (Signature)",
            "description": f"Generated Dilithium3 keypair: public key = {len(dilithium_pk)} bytes, secret key = {len(dilithium_sk)} bytes.",
            "details": {"algorithm": crypto_utils.SIG_ALG, "public_key_bytes": len(dilithium_pk),
                        "secret_key_bytes": len(dilithium_sk), "pk_preview": dilithium_pk[:16].hex() + "..."},
            "status": "success",
        })
        rsa_pk, rsa_sk = crypto_utils.generate_rsa_keypair()
        steps.append({
            "step": 3, "title": "Generate RSA-2048 Key Pair (Hybrid)",
            "description": f"Generated RSA-2048 keypair for hybrid mode: public = {len(rsa_pk)} bytes.",
            "details": {"algorithm": "RSA-2048", "public_key_bytes": len(rsa_pk), "private_key_bytes": len(rsa_sk)},
            "status": "success",
        })
        steps.append({
            "step": 4, "title": "Register Public Keys on Server",
            "description": "Public keys submitted to the central key server.",
            "details": {"kyber_pk_bytes": len(kyber_pk), "dilithium_pk_bytes": len(dilithium_pk), "rsa_pk_bytes": len(rsa_pk)},
            "status": "success",
        })
        return {"kyber_pk": kyber_pk, "kyber_sk": kyber_sk,
                "dilithium_pk": dilithium_pk, "dilithium_sk": dilithium_sk,
                "rsa_pk": rsa_pk, "rsa_sk": rsa_sk, "steps": steps}

    # ------------------------------------------------------------------
    # Sender Workflow
    # ------------------------------------------------------------------

    def _build_plaintext(self, subject: str, body: str) -> str:
        msg_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()
        return f"Message-ID: {msg_id}\nTimestamp: {ts}\nSubject: {subject}\n\n{body}"

    def send_email(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        """Compose, sign, encrypt, and send an email."""
        recipient_keys = self.server.get_public_keys(recipient)
        recipient_kyber_pk: bytes = recipient_keys["kyber_pk"]
        plaintext_str = self._build_plaintext(subject, body)
        plaintext: bytes = plaintext_str.encode("utf-8")
        signature: bytes = crypto_utils.sign(plaintext, self.dilithium_sk)
        payload: bytes = crypto_utils.build_payload(signature, plaintext)
        encapsulated_key, shared_secret = crypto_utils.kem_encapsulate(recipient_kyber_pk)
        ciphertext, nonce, tag = crypto_utils.aes_gcm_encrypt(payload, shared_secret)
        package = {"encapsulated_key": encapsulated_key, "ciphertext": ciphertext,
                    "nonce": nonce, "tag": tag}
        self.server.send_message(sender=self.username, recipient=recipient, package=package)
        return package

    def send_email_with_log(self, recipient: str, subject: str, body: str,
                             encrypt_subject: bool = False) -> Dict[str, Any]:
        """Same as send_email but returns step-by-step crypto logs."""
        steps: List[Dict[str, Any]] = []
        recipient_keys = self.server.get_public_keys(recipient)
        recipient_kyber_pk: bytes = recipient_keys["kyber_pk"]
        steps.append({
            "step": 1, "title": "Fetch Recipient's Kyber Public Key",
            "description": f"Retrieved {recipient}'s Kyber768 public key from the server.",
            "details": {"algorithm": crypto_utils.KEM_ALG, "key_size_bytes": len(recipient_kyber_pk),
                        "preview": self._hex_preview(recipient_kyber_pk)},
            "status": "success",
        })

        display_subject = subject
        if encrypt_subject:
            hint = subject[:20] + "..." if len(subject) > 20 else subject
            display_subject = hint
        plaintext_str = self._build_plaintext(subject, body)
        plaintext: bytes = plaintext_str.encode("utf-8")

        signature: bytes = crypto_utils.sign(plaintext, self.dilithium_sk)
        enc_note = " Includes encrypted subject line." if encrypt_subject else ""
        steps.append({
            "step": 2, "title": "Sign Message with Dilithium SK",
            "description": f"Signed the plaintext ({len(plaintext)} bytes) using {self.username}'s Dilithium secret key.{enc_note}",
            "details": {"algorithm": crypto_utils.SIG_ALG, "plaintext_size_bytes": len(plaintext),
                        "signature_size_bytes": len(signature), "signature_preview": self._hex_preview(signature)},
            "status": "success",
        })

        payload: bytes = crypto_utils.build_payload(signature, plaintext)
        steps.append({
            "step": 3, "title": "Build Combined Payload",
            "description": "Combined [4-byte sig_len] || signature || message into a single payload.",
            "details": {"format": "[4B length prefix][signature][message]", "signature_size_bytes": len(signature),
                        "message_size_bytes": len(plaintext), "total_payload_bytes": len(payload)},
            "status": "success",
        })

        encapsulated_key, shared_secret = crypto_utils.kem_encapsulate(recipient_kyber_pk)
        steps.append({
            "step": 4, "title": "KEM Encapsulate Shared Secret",
            "description": f"Generated a shared secret using {recipient}'s Kyber public key.",
            "details": {"algorithm": crypto_utils.KEM_ALG, "encapsulated_key_bytes": len(encapsulated_key),
                        "shared_secret_bytes": len(shared_secret),
                        "encapsulated_key_preview": self._hex_preview(encapsulated_key),
                        "shared_secret_preview": self._hex_preview(shared_secret)},
            "status": "success",
        })

        ciphertext, nonce, tag = crypto_utils.aes_gcm_encrypt(payload, shared_secret)
        steps.append({
            "step": 5, "title": "AES-256-GCM Encrypt Payload",
            "description": f"Encrypted the {len(payload)}-byte payload with AES-256-GCM using the KEM shared secret.",
            "details": {"algorithm": "AES-256-GCM", "ciphertext_bytes": len(ciphertext),
                        "nonce_bytes": len(nonce), "tag_bytes": len(tag),
                        "nonce_hex": nonce.hex(), "tag_hex": tag.hex(),
                        "ciphertext_preview": self._hex_preview(ciphertext)},
            "status": "success",
        })

        package = {"encapsulated_key": encapsulated_key, "ciphertext": ciphertext,
                    "nonce": nonce, "tag": tag}
        self.server.send_message(sender=self.username, recipient=recipient, package=package)
        steps.append({
            "step": 6, "title": "Send Package to Server",
            "description": f"Delivered the encrypted package to {recipient}'s mailbox on the server.",
            "details": {"total_package_bytes": len(encapsulated_key) + len(ciphertext) + len(nonce) + len(tag),
                        "components": ["encapsulated_key", "ciphertext", "nonce", "tag"]},
            "status": "success",
        })

        return {"package": package, "steps": steps, "subject": display_subject,
                "encrypt_subject": encrypt_subject, "plaintext_str": plaintext_str}

    # ------------------------------------------------------------------
    # Password-protected send (password-based KDF instead of KEM)
    # ------------------------------------------------------------------

    def send_email_password_protected_with_log(
        self, recipient: str, subject: str, body: str, password: str,
    ) -> Dict[str, Any]:
        """Send with password-derived AES key instead of KEM."""
        steps: List[Dict[str, Any]] = []

        plaintext_str = self._build_plaintext(subject, body)
        plaintext: bytes = plaintext_str.encode("utf-8")

        signature: bytes = crypto_utils.sign(plaintext, self.dilithium_sk)
        steps.append({
            "step": 1, "title": "Sign Message with Dilithium SK",
            "description": f"Signed the plaintext ({len(plaintext)} bytes).",
            "details": {"algorithm": crypto_utils.SIG_ALG, "signature_size_bytes": len(signature)},
            "status": "success",
        })

        payload: bytes = crypto_utils.build_payload(signature, plaintext)

        aes_key, salt = crypto_utils.derive_key_from_password(password)
        steps.append({
            "step": 2, "title": "Derive AES Key from Password (scrypt)",
            "description": "Used scrypt KDF to derive a 32-byte AES key from the password. No KEM needed.",
            "details": {"kdf": "scrypt", "N": 2**14, "r": 8, "p": 1,
                        "salt_hex": salt.hex(), "key_preview": aes_key[:8].hex() + "..."},
            "status": "success",
        })

        ciphertext, nonce, tag = crypto_utils.aes_gcm_encrypt(payload, aes_key)
        steps.append({
            "step": 3, "title": "AES-256-GCM Encrypt Payload",
            "description": f"Encrypted {len(payload)}-byte payload with password-derived AES key.",
            "details": {"algorithm": "AES-256-GCM", "ciphertext_bytes": len(ciphertext)},
            "status": "success",
        })

        package = {"encapsulated_key": salt, "ciphertext": ciphertext,
                    "nonce": nonce, "tag": tag, "password_protected": True}
        self.server.send_message(sender=self.username, recipient=recipient, package=package)
        steps.append({
            "step": 4, "title": "Send Password-Protected Package",
            "description": f"Sent to {recipient}. Recipient needs the password to decrypt.",
            "details": {},
            "status": "success",
        })

        return {"package": package, "steps": steps, "plaintext_str": plaintext_str}

    # ------------------------------------------------------------------
    # Hybrid send (RSA-2048 + Kyber768 + Dilithium3)
    # ------------------------------------------------------------------

    def send_email_hybrid_with_log(
        self, recipient: str, subject: str, body: str,
        recipient_rsa_pk: bytes, encrypt_subject: bool = False,
    ) -> Dict[str, Any]:
        """Send with hybrid RSA+Kyber key establishment for defense-in-depth."""
        steps: List[Dict[str, Any]] = []
        recipient_keys = self.server.get_public_keys(recipient)
        recipient_kyber_pk: bytes = recipient_keys["kyber_pk"]
        steps.append({
            "step": 1, "title": "Fetch Recipient's Kyber + RSA Public Keys",
            "description": f"Retrieved {recipient}'s Kyber768 and RSA-2048 public keys.",
            "details": {"kyber_pk_bytes": len(recipient_kyber_pk), "rsa_pk_bytes": len(recipient_rsa_pk)},
            "status": "success",
        })

        display_subject = subject
        if encrypt_subject:
            hint = subject[:20] + "..." if len(subject) > 20 else subject
            display_subject = hint
        plaintext_str = self._build_plaintext(subject, body)
        plaintext: bytes = plaintext_str.encode("utf-8")

        signature: bytes = crypto_utils.sign(plaintext, self.dilithium_sk)
        steps.append({
            "step": 2, "title": "Sign Message with Dilithium3 SK",
            "description": f"Signed {len(plaintext)}-byte plaintext with Dilithium secret key.",
            "details": {"algorithm": crypto_utils.SIG_ALG, "signature_size_bytes": len(signature)},
            "status": "success",
        })

        payload: bytes = crypto_utils.build_payload(signature, plaintext)

        rsa_ct, kyber_encap, combined_ss = crypto_utils.hybrid_encapsulate(
            recipient_kyber_pk, recipient_rsa_pk
        )
        steps.append({
            "step": 3, "title": "Hybrid KEM: RSA-2048 + Kyber768",
            "description": "Generated 32-byte RSA secret + Kyber shared secret. "
                           "Combined via SHA-256(RSA_secret || Kyber_secret) for final AES key.",
            "details": {
                "rsa_ciphertext_bytes": len(rsa_ct),
                "kyber_encapsulated_bytes": len(kyber_encap),
                "combined_secret_bytes": len(combined_ss),
                "formula": "AES_key = SHA-256(RSA_secret || Kyber_secret)",
            },
            "status": "success",
        })

        ciphertext, nonce, tag = crypto_utils.aes_gcm_encrypt(payload, combined_ss)
        steps.append({
            "step": 4, "title": "AES-256-GCM Encrypt with Hybrid Key",
            "description": f"Encrypted {len(payload)}-byte payload with the hybrid-derived AES-256 key.",
            "details": {"algorithm": "AES-256-GCM", "ciphertext_bytes": len(ciphertext)},
            "status": "success",
        })

        package = {
            "encapsulated_key": kyber_encap,
            "rsa_ciphertext": rsa_ct,
            "ciphertext": ciphertext,
            "nonce": nonce,
            "tag": tag,
            "hybrid": True,
        }
        self.server.send_message(sender=self.username, recipient=recipient, package=package)
        steps.append({
            "step": 5, "title": "Send Hybrid Package to Server",
            "description": f"Delivered RSA+Kyber encrypted package to {recipient}.",
            "details": {
                "total_bytes": len(rsa_ct) + len(kyber_encap) + len(ciphertext) + len(nonce) + len(tag),
                "security_level": "Level 3 — Hybrid Defense-in-Depth",
            },
            "status": "success",
        })

        return {"package": package, "steps": steps, "subject": display_subject,
                "encrypt_subject": encrypt_subject, "plaintext_str": plaintext_str}

    # ------------------------------------------------------------------
    # Forged-signature variant
    # ------------------------------------------------------------------

    def send_email_forged_with_log(self, recipient: str, subject: str, body: str,
                                     forge_sig_sk: bytes, forge_user: str) -> Dict[str, Any]:
        """Send an email signed with the wrong Dilithium secret key."""
        steps: List[Dict[str, Any]] = []
        recipient_keys = self.server.get_public_keys(recipient)
        recipient_kyber_pk: bytes = recipient_keys["kyber_pk"]
        steps.append({
            "step": 1, "title": "Fetch Recipient's Kyber Public Key",
            "description": f"Retrieved {recipient}'s Kyber768 public key from the server.",
            "details": {"algorithm": crypto_utils.KEM_ALG, "key_size_bytes": len(recipient_kyber_pk)},
            "status": "success",
        })

        plaintext_str = self._build_plaintext(subject, body)
        plaintext: bytes = plaintext_str.encode("utf-8")

        signature: bytes = crypto_utils.sign(plaintext, forge_sig_sk)
        steps.append({
            "step": 2, "title": "FORGED Signature (Wrong Dilithium SK!)",
            "description": f"Signed with {forge_user}'s Dilithium SK instead of {self.username}'s.",
            "details": {"algorithm": crypto_utils.SIG_ALG, "signed_with": f"{forge_user}'s secret key",
                        "claimed_sender": self.username, "signature_size_bytes": len(signature)},
            "status": "error",
        })

        payload: bytes = crypto_utils.build_payload(signature, plaintext)
        steps.append({"step": 3, "title": "Build Combined Payload",
                       "description": "Combined forged-signature + message into payload.",
                       "details": {"total_payload_bytes": len(payload)}, "status": "success"})

        encapsulated_key, shared_secret = crypto_utils.kem_encapsulate(recipient_kyber_pk)
        steps.append({"step": 4, "title": "KEM Encapsulate Shared Secret",
                       "description": "Encapsulation is valid — only the signature is forged.",
                       "details": {"algorithm": crypto_utils.KEM_ALG}, "status": "success"})

        ciphertext, nonce, tag = crypto_utils.aes_gcm_encrypt(payload, shared_secret)
        steps.append({"step": 5, "title": "AES-256-GCM Encrypt (Ciphertext Intact)",
                       "description": "Encryption correct — GCM tag will verify. Only Dilithium sig is wrong.",
                       "details": {"algorithm": "AES-256-GCM"}, "status": "success"})

        package = {"encapsulated_key": encapsulated_key, "ciphertext": ciphertext,
                    "nonce": nonce, "tag": tag}
        self.server.send_message(sender=self.username, recipient=recipient, package=package)
        steps.append({"step": 6, "title": "Send Forged Package to Server",
                       "description": f"Forged package sent to {recipient}. GCM will PASS but Dilithium FAIL.",
                       "details": {}, "status": "error"})

        return {"package": package, "steps": steps, "plaintext_str": plaintext_str}

    # ------------------------------------------------------------------
    # Receive with logging
    # ------------------------------------------------------------------

    def receive_emails(self) -> List[Dict[str, Any]]:
        messages = self.server.fetch_messages(self.username)
        results: List[Dict[str, Any]] = []
        for msg in messages:
            sender: str = msg["sender"]
            try:
                result = self._process_message(msg)
                results.append(result)
            except Exception as exc:
                results.append({"sender": sender, "verified": False,
                                "error": f"{type(exc).__name__}: {exc}"})
        return results

    def receive_emails_with_log(self, password: Optional[str] = None) -> Dict[str, Any]:
        """Same as receive_emails but with step-by-step logs."""
        all_steps: List[Dict[str, Any]] = []
        results: List[Dict[str, Any]] = []
        messages = self.server.fetch_messages(self.username)
        all_steps.append({
            "step": 1, "title": "Fetch Encrypted Packages",
            "description": f"Retrieved {len(messages)} pending message(s) from the server.",
            "details": {"message_count": len(messages)},
            "status": "success" if messages else "info",
        })

        if not messages:
            return {"results": [], "steps": all_steps}

        for idx, msg in enumerate(messages):
            sender: str = msg["sender"]
            step_base = len(all_steps)
            try:
                if msg.get("password_protected") and password:
                    result, msg_steps = self._process_password_message_with_log(
                        msg, password, step_offset=step_base
                    )
                else:
                    result, msg_steps = self._process_message_with_log(msg, step_offset=step_base)
                all_steps.extend(msg_steps)
                results.append(result)
            except Exception as exc:
                all_steps.append({"step": step_base + 1, "title": "Processing Failed",
                                   "description": str(exc), "details": {}, "status": "error"})
                results.append({"sender": sender, "verified": False,
                                "error": f"{type(exc).__name__}: {exc}"})

        return {"results": results, "steps": all_steps}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hex_preview(data: bytes, length: int = 32) -> str:
        full = data.hex()
        return full[:length] + "..." if len(full) > length else full

    def _process_message(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        sender: str = msg["sender"]
        if msg.get("hybrid") and "rsa_ciphertext" in msg:
            shared_secret = crypto_utils.hybrid_decapsulate(
                msg["rsa_ciphertext"], msg["encapsulated_key"], self.rsa_sk, self.kyber_sk
            )
        else:
            shared_secret = crypto_utils.kem_decapsulate(msg["encapsulated_key"], self.kyber_sk)
        try:
            payload = crypto_utils.aes_gcm_decrypt(msg["ciphertext"], shared_secret, msg["nonce"], msg["tag"])
        except ValueError as exc:
            return {"sender": sender, "verified": False,
                    "error": f"AES-GCM decryption failed — data may have been tampered with. ({exc})"}
        signature, plaintext_bytes = crypto_utils.split_payload(payload)
        sender_keys = self.server.get_public_keys(sender)
        is_valid = crypto_utils.verify(plaintext_bytes, signature, sender_keys["dilithium_pk"])
        if not is_valid:
            return {"sender": sender, "verified": False, "plaintext": plaintext_bytes.decode("utf-8"),
                    "error": "Dilithium signature verification FAILED."}
        return {"sender": sender, "verified": True, "plaintext": plaintext_bytes.decode("utf-8")}

    def _process_message_with_log(self, msg: Dict[str, Any], step_offset: int = 0) -> tuple:
        steps: List[Dict[str, Any]] = []
        sender: str = msg["sender"]
        encapsulated_key = msg["encapsulated_key"]
        ciphertext = msg["ciphertext"]
        nonce = msg["nonce"]
        tag = msg["tag"]
        is_hybrid = msg.get("hybrid", False)

        if is_hybrid and "rsa_ciphertext" in msg:
            shared_secret = crypto_utils.hybrid_decapsulate(
                msg["rsa_ciphertext"], encapsulated_key, self.rsa_sk, self.kyber_sk
            )
            steps.append({
                "step": step_offset + 1, "title": "Hybrid Decapsulate (RSA-2048 + Kyber768)",
                "description": f"Decapsulated combined shared secret: RSA-OAEP decrypt + Kyber decap, then SHA-256.",
                "details": {
                    "rsa_ciphertext_bytes": len(msg["rsa_ciphertext"]),
                    "kyber_encapsulated_bytes": len(encapsulated_key),
                    "combined_secret_bytes": len(shared_secret),
                    "formula": "AES_key = SHA-256(RSA_secret || Kyber_secret)",
                    "security_level": "Level 3 — Hybrid Defense-in-Depth",
                },
                "status": "success",
            })
        else:
            shared_secret = crypto_utils.kem_decapsulate(encapsulated_key, self.kyber_sk)
            steps.append({
                "step": step_offset + 1, "title": "KEM Decapsulate Shared Secret",
                "description": f"Decapsulated the shared secret from {sender}'s encapsulated key.",
                "details": {"algorithm": crypto_utils.KEM_ALG, "encapsulated_key_bytes": len(encapsulated_key),
                            "shared_secret_bytes": len(shared_secret),
                            "shared_secret_preview": self._hex_preview(shared_secret)},
                "status": "success",
            })

        try:
            payload = crypto_utils.aes_gcm_decrypt(ciphertext, shared_secret, nonce, tag)
        except ValueError as exc:
            steps.append({"step": step_offset + 2, "title": "AES-256-GCM Decryption FAILED",
                           "description": "GCM tag verification failed. The ciphertext has been tampered with.",
                           "details": {"algorithm": "AES-256-GCM", "error": str(exc)}, "status": "error"})
            return {"sender": sender, "verified": False,
                    "error": f"AES-GCM decryption failed — data tampered. ({exc})"}, steps

        steps.append({
            "step": step_offset + 2, "title": "AES-256-GCM Decrypt Ciphertext",
            "description": f"Decrypted {len(ciphertext)}-byte ciphertext and verified GCM tag.",
            "details": {"algorithm": "AES-256-GCM", "decrypted_payload_bytes": len(payload)},
            "status": "success",
        })

        signature, plaintext_bytes = crypto_utils.split_payload(payload)
        steps.append({
            "step": step_offset + 3, "title": "Split Payload into Signature + Message",
            "description": "Separated Dilithium signature from plaintext using 4-byte length prefix.",
            "details": {"signature_size_bytes": len(signature), "message_size_bytes": len(plaintext_bytes),
                        "signature_preview": self._hex_preview(signature)},
            "status": "success",
        })

        sender_keys = self.server.get_public_keys(sender)
        sender_dilithium_pk = sender_keys["dilithium_pk"]
        steps.append({
            "step": step_offset + 4, "title": "Fetch Sender's Dilithium Public Key",
            "description": f"Retrieved {sender}'s Dilithium public key for verification.",
            "details": {"algorithm": crypto_utils.SIG_ALG, "key_size_bytes": len(sender_dilithium_pk)},
            "status": "success",
        })

        is_valid = crypto_utils.verify(plaintext_bytes, signature, sender_dilithium_pk)
        if is_valid:
            steps.append({"step": step_offset + 5, "title": "Signature Verification PASSED",
                           "description": f"The Dilithium signature from {sender} is VALID.",
                           "details": {"result": "VALID"}, "status": "success"})
        else:
            steps.append({"step": step_offset + 5, "title": "Signature Verification FAILED",
                           "description": f"The Dilithium signature from {sender} is INVALID.",
                           "details": {"result": "INVALID"}, "status": "error"})
            return {"sender": sender, "verified": False, "plaintext": plaintext_bytes.decode("utf-8"),
                    "error": "Dilithium signature verification FAILED."}, steps

        plaintext_decoded = plaintext_bytes.decode("utf-8")
        message_id = None
        for line in plaintext_decoded.split("\n"):
            if line.startswith("Message-ID: "):
                message_id = line.split("Message-ID: ", 1)[1].strip()
                break

        if message_id and message_id in self.seen_message_ids:
            steps.append({"step": step_offset + 6, "title": "REPLAY ATTACK DETECTED",
                           "description": f"Message-ID {message_id} has already been received.",
                           "details": {"message_id": message_id}, "status": "error"})
            return {"sender": sender, "verified": False, "plaintext": plaintext_decoded,
                    "error": f"Replay attack detected: duplicate Message-ID {message_id}"}, steps

        if message_id:
            self.seen_message_ids.add(message_id)

        steps.append({
            "step": step_offset + 6, "title": "Replay Detection — PASSED",
            "description": "Message-ID is unique. No replay detected.",
            "details": {"message_id": message_id or "(none)", "seen_ids_count": len(self.seen_message_ids)},
            "status": "success",
        })

        return {"sender": sender, "verified": True, "plaintext": plaintext_decoded}, steps

    def _process_password_message_with_log(
        self, msg: Dict[str, Any], password: str, step_offset: int = 0
    ) -> tuple:
        """Decrypt a password-protected message using scrypt KDF."""
        steps: List[Dict[str, Any]] = []
        sender = msg["sender"]
        salt = msg["encapsulated_key"]  # salt stored in place of encapsulated_key

        aes_key, _ = crypto_utils.derive_key_from_password(password, salt)
        steps.append({
            "step": step_offset + 1, "title": "Derive AES Key from Password (scrypt)",
            "description": "Used scrypt KDF with provided password and transmitted salt.",
            "details": {"kdf": "scrypt", "salt_hex": salt.hex()},
            "status": "success",
        })

        try:
            payload = crypto_utils.aes_gcm_decrypt(msg["ciphertext"], aes_key, msg["nonce"], msg["tag"])
        except ValueError as exc:
            steps.append({"step": step_offset + 2, "title": "Decryption FAILED — Wrong Password?",
                           "description": "GCM tag verification failed. Likely incorrect password.",
                           "details": {"error": str(exc)}, "status": "error"})
            return {"sender": sender, "verified": False,
                    "error": f"Password decryption failed. ({exc})"}, steps

        steps.append({"step": step_offset + 2, "title": "AES-256-GCM Decrypt with Password Key",
                       "description": "Decrypted successfully with password-derived key.",
                       "details": {"payload_bytes": len(payload)}, "status": "success"})

        signature, plaintext_bytes = crypto_utils.split_payload(payload)
        sender_keys = self.server.get_public_keys(sender)
        is_valid = crypto_utils.verify(plaintext_bytes, signature, sender_keys["dilithium_pk"])
        if is_valid:
            steps.append({"step": step_offset + 3, "title": "Signature Verification PASSED",
                           "description": f"Dilithium signature from {sender} is VALID.",
                           "details": {"result": "VALID"}, "status": "success"})
        else:
            steps.append({"step": step_offset + 3, "title": "Signature Verification FAILED",
                           "description": "Signature invalid.", "details": {}, "status": "error"})
            return {"sender": sender, "verified": False, "plaintext": plaintext_bytes.decode("utf-8"),
                    "error": "Dilithium signature verification FAILED."}, steps

        plaintext_decoded = plaintext_bytes.decode("utf-8")
        return {"sender": sender, "verified": True, "plaintext": plaintext_decoded,
                "password_protected": True}, steps
