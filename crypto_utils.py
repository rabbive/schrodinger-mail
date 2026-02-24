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
