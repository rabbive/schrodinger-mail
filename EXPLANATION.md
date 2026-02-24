# Schrödinger Mail — Project Explanation

## What is Schrödinger Mail?

**Schrödinger Mail** is a **fully working email client** that uses **post-quantum cryptography** to protect emails. Unlike normal email (Gmail, Outlook) which uses RSA or ECDSA that quantum computers can break, our system uses **NIST-standardized quantum-resistant algorithms** that remain secure even against future quantum attacks.

The name comes from Schrödinger's cat — just like the cat is both alive and dead until observed, your email is both secure and insecure until a quantum computer tries to break it. We make sure it stays secure.

It is built as a web application (Flask + HTML/JS) where users can send, receive, and manage emails — with every message being **signed, encrypted, and verified** using post-quantum algorithms behind the scenes. The entire cryptographic process is visualized step-by-step in the UI.

---

## The Problem We're Solving

**Current encryption is at risk.**

Today's email security relies on algorithms like RSA and ECDSA. These are based on mathematical problems (integer factorization, discrete logarithm) that a sufficiently powerful quantum computer can solve in polynomial time using **Shor's Algorithm**.

The real-world threat is called **"Harvest Now, Decrypt Later"** — adversaries can record encrypted email traffic today and decrypt it years from now when quantum computers become available. Sensitive government, military, and corporate communications are already at risk.

**Our solution:** Replace vulnerable classical algorithms with **NIST-approved post-quantum algorithms** while keeping the user experience identical to a normal email client.

---

## How It Works — The Signed KEM-DEM Architecture

Our system follows a **Sign-then-Encrypt** design called **Signed KEM-DEM**. Here's the flow in plain English:

### When Alice sends an email to Bob:

```
Step 1: SIGN — Alice signs the email with her private signing key (Dilithium3)
        This proves the email genuinely came from Alice and hasn't been modified.

Step 2: PACKAGE — The signature and email are combined into a single payload.
        Format: [signature length][signature][email content]

Step 3: KEY EXCHANGE — Alice generates a one-time shared secret using Bob's
        public encryption key (Kyber768). This is called Key Encapsulation (KEM).
        Only Bob can recover this shared secret using his private key.

Step 4: ENCRYPT — The signed payload is encrypted using AES-256-GCM with the
        shared secret as the key. This is the Data Encapsulation (DEM) step.

Step 5: SEND — The encrypted package (encapsulated key + ciphertext + nonce + tag)
        is delivered to Bob's mailbox on the server.
```

### When Bob receives the email:

```
Step 1: FETCH — Bob downloads the encrypted package from the server.

Step 2: KEY RECOVERY — Bob uses his private Kyber key to decapsulate the
        shared secret from the encapsulated key.

Step 3: DECRYPT — Bob decrypts the ciphertext using AES-256-GCM. If even one
        byte was tampered with, the GCM authentication tag fails and the
        message is rejected.

Step 4: VERIFY — Bob extracts Alice's signature from the payload and verifies
        it using Alice's public signing key (Dilithium3). If the signature
        doesn't match, the email is marked as forged.

Step 5: REPLAY CHECK — Bob checks the Message-ID against previously seen IDs.
        Duplicate messages (replay attacks) are detected and flagged.
```

---

## The Three Algorithms We Use

### 1. CRYSTALS-Kyber768 (Key Encapsulation)

- **Purpose:** Securely exchange a shared secret between sender and receiver
- **Standard:** NIST FIPS 203 (ML-KEM-768)
- **Security:** NIST Level 3 (equivalent to AES-192)
- **How it works:** Based on the **Module Learning With Errors (MLWE)** problem — a lattice-based problem that quantum computers cannot efficiently solve
- **Key sizes:** Public key = 1,184 bytes, Secret key = 2,400 bytes
- **Output:** A 32-byte shared secret that becomes the AES-256 key

### 2. CRYSTALS-Dilithium3 (Digital Signatures)

- **Purpose:** Prove who sent the email and that it wasn't modified
- **Standard:** NIST FIPS 204 (ML-DSA-65)
- **Security:** NIST Level 3, EUF-CMA secure
- **How it works:** Also lattice-based (MLWE + MSIS problems). The signer uses their secret key to create a signature that anyone can verify with the public key, but no one can forge.
- **Key sizes:** Public key = 1,952 bytes, Secret key = 4,000 bytes
- **Signature:** ~3,293 bytes per message

### 3. AES-256-GCM (Symmetric Encryption)

- **Purpose:** Actually encrypt the email content
- **Standard:** NIST SP 800-38D
- **Security:** 256-bit key = 128-bit post-quantum security (Grover's algorithm halves the effective key length)
- **How it works:** Encrypts data and produces an authentication tag. If anyone tampers with the ciphertext, the tag check fails during decryption.
- **Parameters:** 12-byte nonce, 16-byte authentication tag

---

## Three Security Levels

We offer selectable security levels in the compose form:

| Level | Name | How Key Is Established | When to Use |
|-------|------|----------------------|-------------|
| **Level 1** | Password-Protected | scrypt KDF derives AES key from a shared password | When both parties know a password |
| **Level 2** | Post-Quantum (Default) | Kyber768 KEM generates the AES key | Standard use — quantum-safe |
| **Level 3** | Hybrid Defense-in-Depth | RSA-2048 + Kyber768 combined | Maximum security during PQC transition |

**Level 3 explained:** The AES key is derived as `SHA-256(RSA_secret || Kyber_secret)`. Even if one algorithm (RSA or Kyber) is broken in the future, the other still protects the key. This follows NIST's recommended approach for the transition period.

---

## Security Demonstrations (Interactive)

The UI includes live attack simulations that prove the cryptographic protections work:

### 1. Tamper Detection
- We flip one byte in the encrypted ciphertext (simulating a man-in-the-middle)
- When the receiver decrypts, the AES-GCM authentication tag fails
- **Result:** Message is rejected. Proves integrity protection.

### 2. Signature Forgery
- We sign a message with the **wrong user's** Dilithium key
- The receiver's verification check uses the claimed sender's public key
- **Result:** Signature verification fails. Proves authenticity protection.

### 3. Replay Attack
- We duplicate a message in the server's mailbox
- The receiver checks Message-IDs against previously seen messages
- **Result:** Duplicate is detected and flagged. Proves replay protection.

---

## Project Architecture

```
Browser (UI)
    |
    | REST API (JSON)
    |
Flask Server (app.py)
    |
    |--- client.py      Crypto workflows (sign, encrypt, decrypt, verify)
    |--- crypto_utils.py Low-level primitives (Kyber, Dilithium, AES, RSA)
    |--- server.py       Simulated key directory + mail relay
    |--- database.py     SQLite persistence (10 tables)
    |--- config.py       Environment-based settings
```

### Key Files Explained

| File | Lines | What It Does |
|------|-------|-------------|
| `crypto_utils.py` | ~550 | All crypto: Kyber keygen/encap/decap, Dilithium sign/verify, AES encrypt/decrypt, RSA hybrid, payload encoding, benchmarks |
| `client.py` | ~550 | Sender/receiver workflows with step-by-step logging for the UI |
| `server.py` | ~150 | In-memory key directory and message relay (simulates a mail server) |
| `database.py` | ~650 | SQLite storage for users, emails, drafts, contacts, sessions, audit log |
| `app.py` | ~900 | Flask web server with 25+ API endpoints |
| `index.html` | ~1400 | Single-page web UI with 10+ panels |

---

## Features Summary

**Email:** Inbox, Sent, Drafts, Archive, Trash, Reply, Forward, Search, Read/Unread, Contacts, Signatures, Encrypted Subjects

**Security:** Argon2id authentication, session management, audit logging, rate limiting, CSRF protection, replay detection

**Educational:** Step-by-step crypto visualization, architecture diagram, threat model panel, classical vs PQC comparison table, downloadable security report

**DevOps:** 109 automated tests (pytest), Docker deployment, GitHub Actions CI

---

## Why This Matters (for SIH)

1. **Real threat:** NIST has already standardized PQC algorithms (Aug 2024) because the quantum threat is imminent
2. **Working prototype:** Not just a demo — it's a full email client with real encryption
3. **Multiple security levels:** Including hybrid RSA+Kyber (defense-in-depth) that most competitors lack
4. **Educational value:** Step-by-step visualization teaches how PQC works
5. **Attack demonstrations:** Proves the system actually detects tampering, forgery, and replay
6. **Production-ready practices:** Tests, Docker, CI, audit logging, rate limiting

---

## How to Demo It

```bash
# Start the app
python app.py
# Open http://127.0.0.1:5001

# Demo flow:
# 1. Switch to Alice, compose an email to Bob → Click "Send Encrypted"
#    → Watch the 6-step crypto process in the right panel
# 2. Switch to Bob, click "Check Mail"
#    → Watch the 6-step decryption + verification process
# 3. Try "Tamper Demo" → Switch to Bob → Check Mail → See rejection
# 4. Try "Forge Sig Demo" → Switch to Bob → Check Mail → See forgery detected
# 5. Change Security Level to "Level 3 (Hybrid)" → Send → See RSA+Kyber steps
# 6. Show the Key Management, Benchmarks, Threat Model, and Architecture panels
```
