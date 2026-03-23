# Schrödinger Mail

A production-oriented, quantum-secure email platform that demonstrates how to build modern encrypted messaging with **NIST-standardized post-quantum cryptography**. Schrödinger Mail combines a Flask backend and React frontend with a **Signed KEM-DEM** pipeline to deliver confidentiality, integrity, and authenticity against both classical and quantum-era threats.

**GitHub repo bio (copy/paste):**  
Schrödinger Mail is a post-quantum secure email platform built with Kyber, Dilithium, and AES-GCM, featuring signed KEM-DEM encryption, modern web UX, and production-ready deployment assets.

## Why this repository exists

This project is designed as both:
- an **applied security engineering prototype** for post-quantum communication systems, and
- an **educational reference implementation** for teams transitioning from classical public-key cryptography to PQC-safe workflows.

> Developed for the Smart India Hackathon (SIH) — Blockchain & Cybersecurity track.

---

## Cryptographic Suite

| Layer | Algorithm | Standard | Security Level |
|-------|-----------|----------|----------------|
| **Key Encapsulation (KEM)** | CRYSTALS-Kyber768 | FIPS 203 (ML-KEM-768) | NIST Level 3 |
| **Digital Signatures** | CRYSTALS-Dilithium3 | FIPS 204 (ML-DSA-65) | NIST Level 3 |
| **Symmetric Encryption** | AES-256-GCM | NIST SP 800-38D | 256-bit |
| **Hybrid Mode (Optional)** | RSA-2048 + Kyber768 | NIST SP 800-56B + FIPS 203 | Defense-in-depth |
| **Password KDF** | scrypt | RFC 7914 | N=16384, r=8, p=1 |
| **Password Hashing** | Argon2id | RFC 9106 | Memory-hard |

---

## Architecture

### Signed KEM-DEM Pipeline

The system follows a **Sign-then-Encrypt** workflow where the sender's identity is cryptographically bound to every message:

```
SENDER WORKFLOW                          RECEIVER WORKFLOW
═══════════════                          ════════════════

1. Sign plaintext with                   1. Fetch encrypted package
   Dilithium secret key                     from server
        │                                        │
        ▼                                        ▼
2. Build payload:                        2. KEM Decapsulate shared
   [sig_len][signature][message]            secret with Kyber SK
        │                                        │
        ▼                                        ▼
3. KEM Encapsulate shared                3. AES-256-GCM Decrypt +
   secret with recipient's                  verify GCM tag
   Kyber public key                              │
        │                                        ▼
        ▼                                4. Split payload into
4. AES-256-GCM Encrypt                     signature + plaintext
   payload with shared secret                    │
        │                                        ▼
        ▼                                5. Verify Dilithium
5. Transmit encrypted package               signature with sender's
   to server                                public key
```

### Three Security Levels

| Level | Name | KEM | Signature | Use Case |
|-------|------|-----|-----------|----------|
| **Level 1** | Password-Protected | scrypt KDF | Dilithium3 | Shared-password messages |
| **Level 2** | Post-Quantum (Default) | Kyber768 | Dilithium3 | Standard quantum-resistant |
| **Level 3** | Hybrid Defense-in-Depth | RSA-2048 + Kyber768 | Dilithium3 | Maximum security |

**Level 3 Hybrid Mode** derives the AES key from `SHA-256(RSA_secret || Kyber_secret)`, ensuring security holds even if one algorithm is broken. This follows NIST's recommended hybrid approach for the PQC transition period.

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (Client)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ Compose  │ │  Inbox   │ │  Keys    │ │  Security Panels  │  │
│  │  Form    │ │  Reader  │ │  Manager │ │  (Architecture,   │  │
│  │          │ │  Folders │ │  Export  │ │   Threats, PQC)   │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───────────────────┘  │
│       └─────────────┴────────────┘                               │
│                      │ REST API                                  │
├──────────────────────┼───────────────────────────────────────────┤
│                      ▼                                           │
│              Flask Web Server (app.py)                            │
│  ┌──────────────┐ ┌───────────────┐ ┌─────────────────────────┐ │
│  │ Auth +       │ │ Rate Limiting │ │ CSRF Protection         │ │
│  │ Sessions     │ │ (flask-limiter│ │ (per-session tokens)    │ │
│  │ (Argon2id)   │ │  200/min)     │ │                         │ │
│  └──────┬───────┘ └───────────────┘ └─────────────────────────┘ │
│         ▼                                                        │
│  ┌──────────────┐ ┌───────────────┐ ┌─────────────────────────┐ │
│  │ client.py    │ │ server.py     │ │ crypto_utils.py         │ │
│  │ Send/Receive │ │ Key Directory │ │ Kyber + Dilithium + AES │ │
│  │ Sign/Verify  │ │ Mail Relay    │ │ Hybrid RSA + Benchmarks │ │
│  └──────┬───────┘ └───────────────┘ └─────────────────────────┘ │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  SQLite (database.py)                        │ │
│  │  users · emails · pending · drafts · contacts · attachments │ │
│  │  sessions · audit_log · seen_ids · user_settings            │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## Features

### Email Client (30+ features)
- **Folder System**: Inbox, Sent, Drafts, Archive, Trash with unread counts
- **Compose**: Rich compose form with recipient selection, subject, body
- **Reply / Forward**: Pre-filled compose with quoted original text
- **Drafts**: Auto-save every 30 seconds, manual save, load back into compose
- **Search**: Full-text search across sender, subject, and body
- **Read/Unread**: Visual indicators, mark-as-read on open
- **Contacts**: Address book with fingerprint tracking and verification
- **Email Signatures**: Per-user configurable signature appended to outgoing mail
- **Encrypted Subject Lines**: Tuta-style encrypted subjects (subject inside ciphertext)
- **Desktop Notifications**: Browser Notification API for new mail
- **Keyboard Shortcuts**: `C` compose, `/` search, `Esc` close, `?` help

### Security
- **Argon2id Authentication**: Password hashing with memory-hard KDF
- **Session Management**: View active sessions, revoke any session
- **Audit Log**: Every security-relevant event logged with timestamp and IP
- **Rate Limiting**: Configurable per-endpoint limits (flask-limiter)
- **CSRF Protection**: Per-session tokens on all mutating endpoints
- **Replay Detection**: Persistent Message-ID tracking survives server restarts
- **Input Validation**: Max lengths on subject (500), body (50K), username (32)
- **Thread-Safe DB**: All SQLite writes serialized through threading lock

### Security Demos (Interactive)
- **Tamper Detection**: Flip a ciphertext byte, watch GCM tag verification fail
- **Signature Forgery**: Sign with wrong Dilithium key, see verification reject it
- **Replay Attack**: Duplicate a message, see Message-ID detection catch it
- **Password-Protected Messages**: scrypt KDF key derivation instead of KEM
- **Hybrid Encryption**: RSA+Kyber combined key establishment

### Key Management
- **SHA-256 Fingerprints**: Grouped hex display of public key hashes
- **Key Export**: Download Kyber/Dilithium public keys as `.bin` files
- **Key Verification**: Side-by-side fingerprint comparison between users
- **Key Size Visualization**: Bar chart comparing all key sizes

### Educational Panels
- **Crypto Architecture Diagram**: Interactive sender/receiver workflow visualization
- **Classical vs PQC Comparison**: Side-by-side table (RSA/ECDSA vs Kyber/Dilithium)
- **Threat Model**: 10 threat categories with protection status
- **Crypto Process Log**: Real-time step-by-step visualization of every operation
- **Security Report Export**: Downloadable HTML report with algorithms, keys, benchmarks, audit log

### UX
- **Dark / Light Theme**: Toggle with `localStorage` persistence
- **Mobile Responsive**: CSS breakpoints at 900px and 1100px
- **Loading States**: Global spinner overlay for long operations
- **Performance Benchmarks**: Timed crypto operations (5 iterations avg)

---

## Quick Start

### Prerequisites

- Python 3.10+
- [liboqs](https://github.com/open-quantum-safe/liboqs) C library installed
- pip

### Local Setup

```bash
git clone https://github.com/rabbive/schrodinger-mail.git
cd schrodinger-mail

python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

pip install -r requirements.txt

python app.py
# Open http://127.0.0.1:5001
```

### Docker (One Command)

```bash
docker compose up --build
# Open http://localhost:5001
```

### Running Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## Project Structure

```
schrodinger-mail/
├── app.py              # Flask web server — all API routes (~900 lines)
├── client.py           # Client-side crypto workflows — send/receive (~500 lines)
├── server.py           # Simulated key directory + mail relay
├── crypto_utils.py     # All cryptographic primitives — Kyber, Dilithium, AES, RSA
├── database.py         # SQLAlchemy persistence — SQLite dev, PostgreSQL prod
├── config.py           # Environment-based configuration
├── demo.py             # CLI demonstration (backward compatible)
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container image
├── docker-compose.yml  # One-command deployment (app + optional Postgres + nginx)
├── SECURITY.md         # Security analysis and threat model
├── templates/
│   ├── home.html       # New landing page with login + demo button
│   └── index.html      # Single-page web application (~1400 lines)
└── tests/
    ├── test_crypto.py  # Crypto primitives tests
    ├── test_api.py     # API endpoint tests
    └── test_database.py# Database CRUD tests
```

---

## Configuration

Environment variables (all optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `QEC_SECRET_KEY` | `dev-secret-change-in-production` | Flask session secret |
| `QEC_DEBUG` | `0` | Set to `1` to enable Flask debug mode |
| `QEC_PORT` | `5001` | Server port |

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/state` | System state (algorithms, users, key info) |
| `POST` | `/api/send` | Send encrypted email (Level 2 default) |
| `POST` | `/api/send-password` | Send password-protected email (Level 1) |
| `POST` | `/api/receive/<user>` | Decrypt pending messages |
| `GET` | `/api/folders/<user>` | Folder list with counts |
| `GET` | `/api/emails/<user>/<folder>` | Emails in folder |
| `POST` | `/api/move/<user>/<id>` | Move email between folders |
| `GET` | `/api/search/<user>?q=` | Full-text search |
| `POST` | `/api/register` | Register new user with key generation |
| `POST` | `/api/auth/login` | Login with Argon2id verification |
| `GET` | `/api/keys/<user>` | Public key fingerprints and sizes |
| `GET` | `/api/keys/export/<user>/<type>` | Download public key binary |
| `POST` | `/api/keys/verify` | Compare fingerprints between users |
| `GET` | `/api/benchmarks` | Run and return crypto benchmarks |
| `GET` | `/api/audit/<user>` | Security audit log |
| `GET` | `/api/report/<user>` | Download HTML security report |
| `POST` | `/api/send-forged` | Demo: forged signature attack |
| `POST` | `/api/tamper/<user>` | Demo: MitM ciphertext tampering |
| `POST` | `/api/replay/<user>` | Demo: replay attack simulation |
| `POST` | `/p2p/incoming` | Receive an encrypted package from a LAN peer (P2P mode) |

---

## Why Post-Quantum?

Quantum computers running **Shor's algorithm** can break RSA, ECDSA, and Diffie-Hellman in polynomial time. While large-scale quantum computers don't exist yet, the **"Harvest Now, Decrypt Later"** threat means adversaries may already be recording encrypted traffic for future decryption.

NIST finalized the first post-quantum standards in **August 2024**:
- **FIPS 203** (ML-KEM / Kyber) — Key Encapsulation
- **FIPS 204** (ML-DSA / Dilithium) — Digital Signatures

This project implements both at **NIST Security Level 3** (equivalent to AES-192 security), with an optional **hybrid RSA+Kyber mode** for defense-in-depth during the transition period.

---

## Security Considerations

See [SECURITY.md](SECURITY.md) for the full threat model and security analysis.
For private vulnerability reporting, see [SECURITY_CONTACT.md](SECURITY_CONTACT.md).

**Key points:**
- This is a **university project/prototype** — not production-hardened
- Private keys are stored server-side (in a production system, they would be client-only)
- The server is trusted (a zero-knowledge architecture would require browser-side PQC)
- SQLite is suitable for demo purposes; production would use PostgreSQL with encrypted storage

---

## Acknowledgments

- [Open Quantum Safe (liboqs)](https://openquantumsafe.org/) — Post-quantum algorithm implementations
- [PyCryptodome](https://www.pycryptodome.org/) — AES-256-GCM symmetric encryption
- [NIST Post-Quantum Cryptography Project](https://csrc.nist.gov/projects/post-quantum-cryptography) — Standardization

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for setup, standards, and PR expectations.
