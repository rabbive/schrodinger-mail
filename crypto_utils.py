#!/usr/bin/env python3
"""
crypto_utils.py — Cryptographic Utility Functions
===================================================
Provides all post-quantum and symmetric cryptographic primitives used by the
Schrödinger Mail (Quantum-Secure P2P Email Client).

Cryptographic Suite
-------------------
* **KEM (Key Encapsulation):** CRYSTALS-Kyber768  (NIST Level 3, IND-CCA2)
* **Digital Signatures:**      CRYSTALS-Dilithium3 / ML-DSA-65  (NIST Level 3, EUF-CMA)
* **Symmetric Encryption:**    AES-256-GCM  (via pycryptodome)

The Kyber768 shared secret is exactly 32 bytes, which maps directly to an
AES-256 key — no additional KDF is required.

Algorithm-name resolution
-------------------------
Different liboqs versions expose either the draft names (``Kyber768``,
``Dilithium3``) or the NIST-standardised names (``ML-KEM-768``,
``ML-DSA-65``).  This module probes for the preferred name first and
falls back automatically so the rest of the application can be
name-agnostic.
"""

from __future__ import annotations

import hashlib
import os
import struct
import time
from typing import Any, Dict, List, Tuple

import oqs
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Protocol.KDF import scrypt
from Crypto.PublicKey import RSA

# ---------------------------------------------------------------------------
# Algorithm name resolution
# ---------------------------------------------------------------------------

# KEM: prefer the user-requested "Kyber768"; fall back to NIST name.
_KEM_CANDIDATES = ("Kyber768", "ML-KEM-768")
# SIG: prefer the user-requested "Dilithium3"; fall back to NIST name.
_SIG_CANDIDATES = ("Dilithium3", "ML-DSA-65")

_enabled_kems = oqs.get_enabled_kem_mechanisms()
_enabled_sigs = oqs.get_enabled_sig_mechanisms()


def _resolve(candidates: tuple[str, ...], enabled: tuple[str, ...]) -> str:
    """Return the first algorithm name from *candidates* that is enabled."""
    for name in candidates:
        if name in enabled:
            return name
    raise RuntimeError(
        f"None of the candidate algorithms {candidates} are enabled in liboqs. "
        f"Enabled algorithms: {enabled}"
    )


KEM_ALG: str = _resolve(_KEM_CANDIDATES, _enabled_kems)
SIG_ALG: str = _resolve(_SIG_CANDIDATES, _enabled_sigs)

# ---------------------------------------------------------------------------
# KEM — Key Encapsulation Mechanism (Kyber768)
# ---------------------------------------------------------------------------


def generate_kem_keypair() -> Tuple[bytes, bytes]:
    """
    Generate a Kyber768 key pair.

    Returns
    -------
    (public_key, secret_key) : tuple[bytes, bytes]
    """
    with oqs.KeyEncapsulation(KEM_ALG) as kem:
        public_key = kem.generate_keypair()
        secret_key = kem.export_secret_key()
    return public_key, secret_key


def kem_encapsulate(public_key: bytes) -> Tuple[bytes, bytes]:
    """
    Encapsulate a fresh shared secret under the recipient's Kyber public key.

    Parameters
    ----------
    public_key : bytes
        Recipient's Kyber public key.

    Returns
    -------
    (encapsulated_key, shared_secret) : tuple[bytes, bytes]
        *encapsulated_key* is transmitted alongside the ciphertext.
        *shared_secret* (32 bytes) is used as the AES-256-GCM key.
    """
    with oqs.KeyEncapsulation(KEM_ALG) as kem:
        encapsulated_key, shared_secret = kem.encap_secret(public_key)
    return encapsulated_key, shared_secret


def kem_decapsulate(encapsulated_key: bytes, secret_key: bytes) -> bytes:
    """
    Decapsulate the shared secret using the recipient's Kyber secret key.

    Parameters
    ----------
    encapsulated_key : bytes
        The KEM ciphertext received from the sender.
    secret_key : bytes
        Recipient's Kyber secret key.

    Returns
    -------
    shared_secret : bytes
        The 32-byte shared secret (AES-256 key).
    """
    with oqs.KeyEncapsulation(KEM_ALG, secret_key) as kem:
        shared_secret = kem.decap_secret(encapsulated_key)
    return shared_secret


# ---------------------------------------------------------------------------
# Digital Signatures — Dilithium3 / ML-DSA-65
# ---------------------------------------------------------------------------


def generate_sig_keypair() -> Tuple[bytes, bytes]:
    """
    Generate a Dilithium3 signature key pair.

    Returns
    -------
    (public_key, secret_key) : tuple[bytes, bytes]
    """
    with oqs.Signature(SIG_ALG) as sig:
        public_key = sig.generate_keypair()
        secret_key = sig.export_secret_key()
    return public_key, secret_key


def sign(message: bytes, secret_key: bytes) -> bytes:
    """
    Sign *message* with a Dilithium3 secret key.

    Parameters
    ----------
    message : bytes
        The data to sign (plaintext email payload).
    secret_key : bytes
        Sender's Dilithium secret key.

    Returns
    -------
    signature : bytes
    """
    with oqs.Signature(SIG_ALG, secret_key) as sig:
        signature = sig.sign(message)
    return signature


def verify(message: bytes, signature: bytes, public_key: bytes) -> bool:
    """
    Verify a Dilithium3 signature.

    Parameters
    ----------
    message : bytes
        The original signed data.
    signature : bytes
        The signature to verify.
    public_key : bytes
        Sender's Dilithium public key.

    Returns
    -------
    bool
        ``True`` if the signature is valid, ``False`` otherwise.
    """
    with oqs.Signature(SIG_ALG) as sig:
        return sig.verify(message, signature, public_key)


# ---------------------------------------------------------------------------
# AES-256-GCM — Symmetric Authenticated Encryption
# ---------------------------------------------------------------------------

_AES_KEY_BYTES = 32   # 256 bits
_GCM_NONCE_BYTES = 12  # 96-bit nonce recommended by NIST SP 800-38D


def aes_gcm_encrypt(plaintext: bytes, key: bytes) -> Tuple[bytes, bytes, bytes]:
    """
    Encrypt *plaintext* with AES-256-GCM.

    Parameters
    ----------
    plaintext : bytes
        Data to encrypt (the combined signature+message payload).
    key : bytes
        32-byte symmetric key (the KEM shared secret).

    Returns
    -------
    (ciphertext, nonce, tag) : tuple[bytes, bytes, bytes]
        *nonce* is 12 bytes; *tag* is 16 bytes (GCM authentication tag).

    Raises
    ------
    ValueError
        If *key* is not exactly 32 bytes.
    """
    if len(key) != _AES_KEY_BYTES:
        raise ValueError(
            f"AES-256-GCM requires a {_AES_KEY_BYTES}-byte key, got {len(key)} bytes."
        )
    nonce = os.urandom(_GCM_NONCE_BYTES)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return ciphertext, nonce, tag


def aes_gcm_decrypt(
    ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes
) -> bytes:
    """
    Decrypt *ciphertext* and verify its GCM authentication tag.

    Parameters
    ----------
    ciphertext : bytes
    key : bytes
        32-byte symmetric key.
    nonce : bytes
        12-byte nonce used during encryption.
    tag : bytes
        16-byte GCM authentication tag.

    Returns
    -------
    plaintext : bytes

    Raises
    ------
    ValueError
        If the tag verification fails (data was tampered with).
    """
    if len(key) != _AES_KEY_BYTES:
        raise ValueError(
            f"AES-256-GCM requires a {_AES_KEY_BYTES}-byte key, got {len(key)} bytes."
        )
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    return plaintext


# ---------------------------------------------------------------------------
# Payload encoding — combine signature + message into a single byte string
# ---------------------------------------------------------------------------

_LEN_PREFIX_FMT = "!I"  # 4-byte unsigned int, big-endian
_LEN_PREFIX_SIZE = struct.calcsize(_LEN_PREFIX_FMT)


def build_payload(signature: bytes, message: bytes) -> bytes:
    """
    Encode a signature and a message into a single payload.

    Layout::

        [4 bytes: signature length (big-endian)] [signature] [message]

    Parameters
    ----------
    signature : bytes
    message : bytes

    Returns
    -------
    payload : bytes
    """
    return struct.pack(_LEN_PREFIX_FMT, len(signature)) + signature + message


def split_payload(payload: bytes) -> Tuple[bytes, bytes]:
    """
    Inverse of :func:`build_payload`.

    Returns
    -------
    (signature, message) : tuple[bytes, bytes]

    Raises
    ------
    ValueError
        If the payload is malformed (too short or length prefix exceeds data).
    """
    if len(payload) < _LEN_PREFIX_SIZE:
        raise ValueError("Payload too short to contain a length prefix.")

    (sig_len,) = struct.unpack(_LEN_PREFIX_FMT, payload[:_LEN_PREFIX_SIZE])

    if _LEN_PREFIX_SIZE + sig_len > len(payload):
        raise ValueError(
            f"Signature length ({sig_len}) exceeds available payload bytes."
        )

    sig_start = _LEN_PREFIX_SIZE
    sig_end = sig_start + sig_len
    signature = payload[sig_start:sig_end]
    message = payload[sig_end:]
    return signature, message


# ---------------------------------------------------------------------------
# Key Fingerprints
# ---------------------------------------------------------------------------

def key_fingerprint(key: bytes) -> str:
    """
    Compute a SHA-256 fingerprint of a public key.
    Returns hex string grouped in 4-char blocks for readability.
    """
    digest = hashlib.sha256(key).hexdigest()
    return " ".join(digest[i:i+4] for i in range(0, len(digest), 4))


def key_fingerprint_short(key: bytes) -> str:
    """Short 16-char fingerprint for display."""
    return hashlib.sha256(key).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Password-based Key Derivation (for password-protected messages)
# ---------------------------------------------------------------------------

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_SALT_LEN = 16


def derive_key_from_password(password: str, salt: bytes | None = None) -> Tuple[bytes, bytes]:
    """
    Derive a 32-byte AES key from a password using scrypt.

    Returns (key, salt) — salt must be transmitted alongside the ciphertext.
    """
    if salt is None:
        salt = os.urandom(_SCRYPT_SALT_LEN)
    key = scrypt(password.encode("utf-8"), salt, 32, N=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return key, salt


# ---------------------------------------------------------------------------
# Hybrid Encryption — RSA-2048 + Kyber768 (Defense-in-Depth)
# ---------------------------------------------------------------------------
# The AES key is derived from SHA-256(RSA_shared_secret || Kyber_shared_secret).
# Security holds even if one algorithm is broken. Follows NIST hybrid guidance.

_RSA_KEY_SIZE = 2048


def generate_rsa_keypair() -> Tuple[bytes, bytes]:
    """
    Generate an RSA-2048 key pair.

    Returns
    -------
    (public_key_pem, private_key_pem) : tuple[bytes, bytes]
        PEM-encoded RSA keys.
    """
    key = RSA.generate(_RSA_KEY_SIZE)
    return key.publickey().export_key(), key.export_key()


def rsa_encrypt(plaintext: bytes, public_key_pem: bytes) -> bytes:
    """Encrypt up to ~190 bytes with RSA-OAEP (SHA-256)."""
    key = RSA.import_key(public_key_pem)
    cipher = PKCS1_OAEP.new(key)
    return cipher.encrypt(plaintext)


def rsa_decrypt(ciphertext: bytes, private_key_pem: bytes) -> bytes:
    """Decrypt RSA-OAEP ciphertext."""
    key = RSA.import_key(private_key_pem)
    cipher = PKCS1_OAEP.new(key)
    return cipher.decrypt(ciphertext)


def hybrid_encapsulate(kyber_pk: bytes, rsa_pk_pem: bytes) -> Tuple[bytes, bytes, bytes]:
    """
    Hybrid KEM: combine RSA-2048 + Kyber768.

    Generates a random 32-byte secret, encrypts it with RSA-OAEP, and also
    encapsulates a Kyber shared secret. The final AES key is:
        SHA-256(rsa_secret || kyber_secret)

    Returns
    -------
    (rsa_ciphertext, kyber_encapsulated_key, combined_shared_secret)
    """
    rsa_secret = os.urandom(32)
    rsa_ct = rsa_encrypt(rsa_secret, rsa_pk_pem)

    kyber_encap, kyber_ss = kem_encapsulate(kyber_pk)

    combined = hashlib.sha256(rsa_secret + kyber_ss).digest()
    return rsa_ct, kyber_encap, combined


def hybrid_decapsulate(
    rsa_ciphertext: bytes,
    kyber_encapsulated_key: bytes,
    rsa_sk_pem: bytes,
    kyber_sk: bytes,
) -> bytes:
    """
    Hybrid KEM decapsulation: recover the combined shared secret.

    Returns
    -------
    combined_shared_secret : bytes (32 bytes)
    """
    rsa_secret = rsa_decrypt(rsa_ciphertext, rsa_sk_pem)
    kyber_ss = kem_decapsulate(kyber_encapsulated_key, kyber_sk)
    return hashlib.sha256(rsa_secret + kyber_ss).digest()


# ---------------------------------------------------------------------------
# Zero-Knowledge Key Encryption (encrypt private keys at rest)
# ---------------------------------------------------------------------------
# Private keys are encrypted with the user's password before storage.
# The server never sees raw private keys when operating in ZK mode.

_ZK_SALT_LEN = 16
_ZK_NONCE_LEN = 12
_ZK_TAG_LEN = 16


def encrypt_key_blob(private_keys: Dict[str, bytes], password: str) -> bytes:
    """
    Encrypt a dict of private keys into a single blob using a password.

    The blob layout is::

        [16B salt][12B nonce][16B tag][ciphertext]

    The AES-256-GCM key is derived from *password* via scrypt.
    """
    import base64 as _b64, json as _json

    serialized = _json.dumps(
        {k: _b64.b64encode(v).decode("ascii") for k, v in private_keys.items()}
    ).encode("utf-8")
    key, salt = derive_key_from_password(password)
    ciphertext, nonce, tag = aes_gcm_encrypt(serialized, key)
    return salt + nonce + tag + ciphertext


def decrypt_key_blob(blob: bytes, password: str) -> Dict[str, bytes]:
    """
    Inverse of :func:`encrypt_key_blob`.

    Raises ``ValueError`` if the password is wrong (GCM tag check fails).
    """
    import base64 as _b64, json as _json

    salt = blob[:_ZK_SALT_LEN]
    nonce = blob[_ZK_SALT_LEN : _ZK_SALT_LEN + _ZK_NONCE_LEN]
    tag = blob[_ZK_SALT_LEN + _ZK_NONCE_LEN : _ZK_SALT_LEN + _ZK_NONCE_LEN + _ZK_TAG_LEN]
    ciphertext = blob[_ZK_SALT_LEN + _ZK_NONCE_LEN + _ZK_TAG_LEN :]
    key, _ = derive_key_from_password(password, salt)
    plaintext = aes_gcm_decrypt(ciphertext, key, nonce, tag)
    data = _json.loads(plaintext.decode("utf-8"))
    return {k: _b64.b64decode(v) for k, v in data.items()}


# ---------------------------------------------------------------------------
# Attachment Encryption
# ---------------------------------------------------------------------------

def encrypt_attachment(data: bytes, key: bytes | None = None) -> Tuple[bytes, bytes]:
    """
    Encrypt attachment data.  Returns ``(encrypted_blob, file_key)``.

    *encrypted_blob* layout: ``[12B nonce][16B tag][ciphertext]``

    If *key* is ``None`` a fresh random 32-byte key is generated.
    """
    if key is None:
        key = os.urandom(32)
    ct, nonce, tag = aes_gcm_encrypt(data, key)
    return nonce + tag + ct, key


def decrypt_attachment(blob: bytes, key: bytes) -> bytes:
    """Inverse of :func:`encrypt_attachment`."""
    nonce = blob[:12]
    tag = blob[12:28]
    ct = blob[28:]
    return aes_gcm_decrypt(ct, key, nonce, tag)


# ---------------------------------------------------------------------------
# Forward-Secrecy Ratchet (Kyber-based)
# ---------------------------------------------------------------------------
# Simplified symmetric ratchet: each message derives the next chain key via
# HKDF-like construction using SHA-256.  A new Kyber DH ratchet step resets
# the chain whenever the receiver replies.

def ratchet_init(shared_secret: bytes) -> Dict[str, bytes]:
    """Initialise a ratchet state from a shared secret."""
    chain_key = hashlib.sha256(b"ratchet-ck-init" + shared_secret).digest()
    return {"chain_key": chain_key, "step": 0}


def ratchet_advance(state: Dict[str, Any]) -> Tuple[bytes, Dict[str, Any]]:
    """
    Advance the symmetric ratchet by one step.

    Returns ``(message_key, new_state)``.  The caller should use
    *message_key* as the AES-256-GCM key and persist *new_state*.
    """
    ck = state["chain_key"]
    step = state.get("step", 0)
    message_key = hashlib.sha256(b"ratchet-mk" + ck + step.to_bytes(4, "big")).digest()
    next_ck = hashlib.sha256(b"ratchet-ck" + ck + step.to_bytes(4, "big")).digest()
    return message_key, {"chain_key": next_ck, "step": step + 1}


def ratchet_dh_step(
    local_kyber_sk: bytes, remote_kyber_pk: bytes, old_state: Dict[str, Any]
) -> Tuple[bytes, bytes, Dict[str, Any]]:
    """
    Perform a DH ratchet step using Kyber KEM.

    Returns ``(encapsulated_key, message_key, new_state)``.
    The encapsulated_key must be sent alongside the ciphertext so the
    receiver can perform the matching decapsulation step.
    """
    encap, new_ss = kem_encapsulate(remote_kyber_pk)
    merged = hashlib.sha256(
        old_state["chain_key"] + new_ss
    ).digest()
    new_state = ratchet_init(merged)
    msg_key, new_state = ratchet_advance(new_state)
    return encap, msg_key, new_state


def ratchet_dh_receive(
    encapsulated_key: bytes, local_kyber_sk: bytes, old_state: Dict[str, Any]
) -> Tuple[bytes, Dict[str, Any]]:
    """
    Receiver side of a DH ratchet step.

    Returns ``(message_key, new_state)``.
    """
    new_ss = kem_decapsulate(encapsulated_key, local_kyber_sk)
    merged = hashlib.sha256(
        old_state["chain_key"] + new_ss
    ).digest()
    new_state = ratchet_init(merged)
    msg_key, new_state = ratchet_advance(new_state)
    return msg_key, new_state


# ---------------------------------------------------------------------------
# Multi-Recipient Encryption
# ---------------------------------------------------------------------------

def multi_recipient_encrypt(
    plaintext: bytes,
    recipients: List[Tuple[str, bytes]],
) -> Tuple[bytes, bytes, bytes, List[Dict[str, Any]]]:
    """
    Encrypt *plaintext* for multiple recipients.

    Parameters
    ----------
    plaintext : bytes
    recipients : list of (username, kyber_pk) tuples

    Returns
    -------
    (ciphertext, nonce, tag, per_recipient_keys)
        *per_recipient_keys* is a list of dicts with ``username`` and
        ``encapsulated_key`` for each recipient.
    """
    symmetric_key = os.urandom(32)
    ct, nonce, tag = aes_gcm_encrypt(plaintext, symmetric_key)

    per_recipient: List[Dict[str, Any]] = []
    for username, kyber_pk in recipients:
        encap, shared_secret = kem_encapsulate(kyber_pk)
        wrapped_ct, wrapped_nonce, wrapped_tag = aes_gcm_encrypt(symmetric_key, shared_secret)
        per_recipient.append({
            "username": username,
            "encapsulated_key": encap,
            "wrapped_key": wrapped_nonce + wrapped_tag + wrapped_ct,
        })
    return ct, nonce, tag, per_recipient


def multi_recipient_decrypt(
    ciphertext: bytes,
    nonce: bytes,
    tag: bytes,
    encapsulated_key: bytes,
    wrapped_key: bytes,
    kyber_sk: bytes,
) -> bytes:
    """Decrypt a multi-recipient message for one specific recipient."""
    shared_secret = kem_decapsulate(encapsulated_key, kyber_sk)
    w_nonce = wrapped_key[:12]
    w_tag = wrapped_key[12:28]
    w_ct = wrapped_key[28:]
    symmetric_key = aes_gcm_decrypt(w_ct, shared_secret, w_nonce, w_tag)
    return aes_gcm_decrypt(ciphertext, symmetric_key, nonce, tag)


# ---------------------------------------------------------------------------
# Performance Benchmarks
# ---------------------------------------------------------------------------

def run_benchmarks(iterations: int = 5) -> List[Dict[str, Any]]:
    """
    Time each cryptographic operation over *iterations* rounds.

    Returns a list of dicts with keys:
        operation, avg_ms, size_bytes
    """
    results: List[Dict[str, Any]] = []
    sample_data = b"Benchmark payload " + os.urandom(128)

    # ── KEM Keygen ────────────────────────────────────────────
    times = []
    pk = sk = b""
    for _ in range(iterations):
        t0 = time.perf_counter()
        pk, sk = generate_kem_keypair()
        times.append((time.perf_counter() - t0) * 1000)
    results.append({
        "operation": "KEM Keygen (Kyber768)",
        "avg_ms": round(sum(times) / len(times), 3),
        "size_bytes": len(pk) + len(sk),
    })

    # ── KEM Encapsulate ───────────────────────────────────────
    times = []
    encap = ss = b""
    for _ in range(iterations):
        t0 = time.perf_counter()
        encap, ss = kem_encapsulate(pk)
        times.append((time.perf_counter() - t0) * 1000)
    results.append({
        "operation": "KEM Encapsulate",
        "avg_ms": round(sum(times) / len(times), 3),
        "size_bytes": len(encap),
    })

    # ── KEM Decapsulate ───────────────────────────────────────
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        kem_decapsulate(encap, sk)
        times.append((time.perf_counter() - t0) * 1000)
    results.append({
        "operation": "KEM Decapsulate",
        "avg_ms": round(sum(times) / len(times), 3),
        "size_bytes": len(ss),
    })

    # ── SIG Keygen ────────────────────────────────────────────
    times = []
    sig_pk = sig_sk = b""
    for _ in range(iterations):
        t0 = time.perf_counter()
        sig_pk, sig_sk = generate_sig_keypair()
        times.append((time.perf_counter() - t0) * 1000)
    results.append({
        "operation": "SIG Keygen (Dilithium3)",
        "avg_ms": round(sum(times) / len(times), 3),
        "size_bytes": len(sig_pk) + len(sig_sk),
    })

    # ── SIG Sign ──────────────────────────────────────────────
    times = []
    signature = b""
    for _ in range(iterations):
        t0 = time.perf_counter()
        signature = sign(sample_data, sig_sk)
        times.append((time.perf_counter() - t0) * 1000)
    results.append({
        "operation": "SIG Sign",
        "avg_ms": round(sum(times) / len(times), 3),
        "size_bytes": len(signature),
    })

    # ── SIG Verify ────────────────────────────────────────────
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        verify(sample_data, signature, sig_pk)
        times.append((time.perf_counter() - t0) * 1000)
    results.append({
        "operation": "SIG Verify",
        "avg_ms": round(sum(times) / len(times), 3),
        "size_bytes": len(signature),
    })

    # ── AES-256-GCM Encrypt ───────────────────────────────────
    aes_key = os.urandom(32)
    times = []
    ct = nonce = tag = b""
    for _ in range(iterations):
        t0 = time.perf_counter()
        ct, nonce, tag = aes_gcm_encrypt(sample_data, aes_key)
        times.append((time.perf_counter() - t0) * 1000)
    results.append({
        "operation": "AES-256-GCM Encrypt",
        "avg_ms": round(sum(times) / len(times), 3),
        "size_bytes": len(ct),
    })

    # ── AES-256-GCM Decrypt ───────────────────────────────────
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        aes_gcm_decrypt(ct, aes_key, nonce, tag)
        times.append((time.perf_counter() - t0) * 1000)
    results.append({
        "operation": "AES-256-GCM Decrypt",
        "avg_ms": round(sum(times) / len(times), 3),
        "size_bytes": len(ct),
    })

    return results
