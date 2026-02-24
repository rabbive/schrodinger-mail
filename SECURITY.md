# Security Analysis — Schrödinger Mail

## Overview

This document describes the security architecture, threat model, cryptographic design decisions, and known limitations of the Quantum-Secure Peer-to-Peer Email Client.

---

## Cryptographic Architecture

### Signed KEM-DEM (Sign-then-Encrypt)

The system uses a **Sign-then-Encrypt** construction:

1. **Sign**: Sender signs the plaintext with Dilithium3 (ML-DSA-65)
2. **Build Payload**: `[4-byte sig_len][signature][plaintext]`
3. **KEM**: Sender encapsulates a shared secret under recipient's Kyber768 public key
4. **Encrypt**: Payload is encrypted with AES-256-GCM using the shared secret
5. **Transmit**: Encrypted package is stored in the server's mailbox

The receiver performs the inverse: KEM decapsulate, AES-GCM decrypt + verify tag, split payload, verify Dilithium signature.

### Why Sign-then-Encrypt?

- **Privacy**: The signature is encrypted, so eavesdroppers cannot learn the sender's identity from the signature alone
- **Non-repudiation**: The plaintext carries the sender's Dilithium signature, providing strong attribution
- **Simplicity**: The construction is well-studied and straightforward to implement correctly

### Security Levels

| Level | KEM | Signature | Symmetric | Use Case |
|-------|-----|-----------|-----------|----------|
| 1 | scrypt KDF (N=16384) | Dilithium3 | AES-256-GCM | Password-protected messages (shared secret) |
| 2 | Kyber768 | Dilithium3 | AES-256-GCM | Standard post-quantum (default) |
| 3 | RSA-2048 + Kyber768 | Dilithium3 | AES-256-GCM | Hybrid defense-in-depth |

**Level 3 Key Derivation**: `AES_key = SHA-256(RSA_secret ∥ Kyber_secret)`. This ensures that if either RSA or Kyber is compromised (but not both), the AES key remains secure. This follows NIST's recommended approach for the PQC transition period.

---

## Threat Model

### Assets to Protect

1. **Email content** (subject, body) — confidentiality
2. **Sender/recipient identity** — privacy
3. **Message authenticity** — integrity and non-repudiation
4. **User credentials** — password hashes
5. **Private keys** — Kyber SK, Dilithium SK, RSA SK

### Threat Actors

| Actor | Capability | Motivation |
|-------|-----------|------------|
| **Passive eavesdropper** | Intercept network traffic | Read email content |
| **Active MitM** | Modify messages in transit | Tamper with or forge messages |
| **Compromised server** | Access all server-side data | Extract keys, read stored data |
| **Quantum adversary** | Run Shor's/Grover's algorithm | Break classical crypto (RSA/ECDSA/DH) |
| **Replay attacker** | Re-send captured messages | Cause confusion or duplicate actions |

### Protections

| Threat | Protection | Status |
|--------|-----------|--------|
| **Quantum key break (Shor)** | Kyber768 (NIST Level 3 KEM) | Protected |
| **Quantum signature break (Shor)** | Dilithium3 (NIST Level 3 SIG) | Protected |
| **Quantum brute-force (Grover)** | AES-256 (128-bit post-quantum security) | Protected |
| **Ciphertext tampering** | AES-256-GCM authentication tag (128-bit) | Protected |
| **Signature forgery** | Dilithium3 EUF-CMA security | Protected |
| **Message replay** | UUID Message-ID tracking, persistent across restarts | Protected |
| **Classical key break** | Hybrid RSA+Kyber mode (Level 3) | Protected |
| **Weak passwords** | Argon2id with memory-hard parameters | Protected |
| **Brute-force login** | Flask-Limiter rate limiting | Protected |
| **CSRF attacks** | Per-session random tokens | Protected |
| **Harvest-now-decrypt-later** | Post-quantum algorithms by default | Protected |
| **Server compromise** | See "Known Limitations" below | **Partially addressed** |

### Interactive Attack Demonstrations

The system includes interactive demonstrations of three attack scenarios:

1. **Ciphertext Tampering**: Flips a byte in the AES-GCM ciphertext. The GCM tag verification fails during decryption, proving integrity protection.

2. **Signature Forgery**: Signs a message with the wrong user's Dilithium secret key. The receiver's signature verification rejects the message, proving authenticity protection.

3. **Replay Attack**: Duplicates a message in the server's mailbox. The receiver detects the duplicate Message-ID and flags it, proving replay protection.

---

## Known Limitations

### 1. Server-Side Key Storage (NOT Zero-Knowledge)

**This is the most significant security limitation.**

In the current implementation, all private keys (Kyber SK, Dilithium SK, RSA SK) are generated and stored on the server. In a production system, private keys should **never leave the client device**.

A true zero-knowledge architecture (like ProtonMail or Tuta) would:
- Generate keys in the browser using Web Crypto API or a JavaScript PQC library
- Encrypt the private key material with the user's password before storing on server
- Perform all decryption and signing operations client-side

**Mitigation**: This is a demo/prototype limitation. The architecture is designed such that migrating to client-side crypto would not change the cryptographic protocol — only the key storage location.

### 2. No TLS/HTTPS

The Flask development server runs over HTTP. In production:
- Use a reverse proxy (nginx) with TLS 1.3
- Ideally, use quantum-resistant TLS (when available)
- Set `Secure`, `HttpOnly`, `SameSite=Strict` cookie flags

### 3. SQLite for Persistence

SQLite is suitable for demos but not for production multi-user deployment:
- No disk encryption at rest (use `sqlcipher` or filesystem encryption)
- Limited concurrent write throughput
- No built-in backup/replication

### 4. In-Memory Mail Server

The `server.py` relay is in-process Python. In production, this would be replaced with:
- A proper SMTP/IMAP server
- Message queuing (Redis, RabbitMQ)
- Network transport layer security

### 5. No Forward Secrecy

The current KEM-DEM design does not provide forward secrecy. If a user's Kyber secret key is compromised, all past messages encrypted to that key can be decrypted.

**Mitigation**: Forward secrecy could be achieved by implementing a ratcheting protocol (similar to Signal's Double Ratchet) with Kyber-based key exchange.

### 6. Signature Algorithm Agility

The system currently hardcodes Kyber768 and Dilithium3. If these algorithms are later found to have vulnerabilities, the system would need code changes. A more robust design would include:
- Algorithm negotiation between peers
- Algorithm identifier in message headers
- Migration path for key rotation

---

## Cryptographic Parameters

| Parameter | Value | Justification |
|-----------|-------|--------------|
| Kyber public key | 1,184 bytes | NIST Level 3 |
| Kyber secret key | 2,400 bytes | NIST Level 3 |
| Kyber ciphertext | 1,088 bytes | NIST Level 3 |
| Kyber shared secret | 32 bytes | Maps directly to AES-256 key |
| Dilithium public key | 1,952 bytes | NIST Level 3 |
| Dilithium secret key | 4,000 bytes | NIST Level 3 |
| Dilithium signature | ~3,293 bytes | NIST Level 3 |
| AES-GCM nonce | 12 bytes | NIST SP 800-38D recommended |
| AES-GCM tag | 16 bytes | 128-bit authentication |
| RSA key size | 2,048 bits | NIST minimum for 2030+ |
| scrypt N | 16,384 | Reasonable for demo |
| scrypt r | 8 | Standard |
| scrypt p | 1 | Standard |
| Argon2id | Default pycryptodome params | Memory-hard |
| Message-ID | UUID v4 (128-bit random) | Negligible collision probability |

---

## Compliance

| Standard | Status |
|----------|--------|
| **NIST FIPS 203** (ML-KEM) | Implemented via liboqs |
| **NIST FIPS 204** (ML-DSA) | Implemented via liboqs |
| **NIST SP 800-38D** (AES-GCM) | Implemented via pycryptodome |
| **RFC 7914** (scrypt) | Implemented via pycryptodome |
| **RFC 9106** (Argon2) | Implemented via argon2-cffi |
| **NIST SP 800-56B** (RSA) | Implemented via pycryptodome (Level 3 hybrid) |

---

## Responsible Disclosure

This is a university project / SIH submission. If you discover a vulnerability, please open a GitHub issue or contact the maintainer directly.
