# Schrödinger Mail v2 — Overview & Features

This document summarizes the **current (v2) architecture and features** of Schrödinger Mail after the production-grade upgrades you just applied. For the original problem statement and deep-dive explanations, see `EXPLANATION.md` and `SECURITY.md`.

---

## 1. High-Level Summary

Schrödinger Mail is a **quantum-secure email client** that demonstrates how to build a modern end-to-end encrypted mail system using **NIST-standardized post-quantum cryptography**:

- **KEM**: CRYSTALS-Kyber768 (ML-KEM-768)
- **Signatures**: CRYSTALS-Dilithium3 / ML-DSA-65
- **Symmetric**: AES-256-GCM
- **Hybrid Option**: RSA-2048 + Kyber768 (defense-in-depth)

The system follows a **Signed KEM-DEM (Sign-then-Encrypt)** pipeline and now includes:

- **Zero-knowledge-ready key storage** (encrypted private keys)
- **JWT-based authentication** with refresh tokens
- **Forward secrecy ratchet** built on Kyber
- **Multi-recipient encryption** and **encrypted attachments**
- A new **React + TypeScript + Tailwind** frontend
- Full **observability, TLS termination, and Kubernetes manifests**

---

## 2. Project Structure

```text
schrodinger-mail/
├── app.py                 # Flask API server (REST + WebSocket events)
├── client.py              # Sender/receiver crypto workflows (KEM-DEM, demos)
├── server.py              # In-memory mail relay + public key registry
├── crypto_utils.py        # Kyber, Dilithium, AES-GCM, RSA, KDFs, ratchets, multi-recipient
├── database.py            # SQLAlchemy persistence (SQLite dev, PostgreSQL prod)
├── models.py              # ORM models (users, emails, drafts, contacts, attachments, ...)
├── config.py              # All configuration & env vars
├── logging_config.py      # Structured JSON logging setup
├── metrics.py             # In-memory Prometheus-style metrics
├── smtp_gateway.py        # SMTP/IMAP integration layer
├── auth.py                # JWT access + refresh tokens, blacklisting
├── alembic/               # Database migrations (001_initial.py, env.py, etc.)
├── frontend/              # React + TypeScript + Tailwind SPA
│   ├── src/               # Components, hooks, API client, types
│   ├── vite.config.ts     # Dev/build config (proxies /api, /socket.io)
│   └── tailwind.config.ts # Design system (colors, fonts)
├── nginx/                 # TLS 1.3 reverse proxy config + cert script
├── k8s/                   # Kubernetes namespace, Deployments, Services, Ingress, PVC
├── tests/                 # Pytest suites (crypto, API, database)
├── Dockerfile             # Multi-stage image build (liboqs + app)
├── docker-compose.yml     # App + Postgres + Nginx (profiles: default, postgres, tls)
├── README.md              # Original detailed README
├── EXPLANATION.md         # Narrative explanation of architecture
├── SECURITY.md            # Threat model and security analysis
└── PROJECT_OVERVIEW.md    # (this file) High-level v2 overview
```

**Untracked / local-only files are ignored via `.gitignore`:**
- Python virtualenvs: `venv/`, `.venv/`
- Bytecode & cache: `__pycache__/`, `*.pyc`, `*.pyo`, `.pytest_cache/`
- Local DB files: `*.db`, `*.db-wal`, `*.db-shm`
- Frontend artefacts: `node_modules/`, `dist/`, `static/`
- Local TLS certs: `nginx/certs/`

---

## 3. Core Features (v2)

### 3.1 Cryptography & Security

- **Signed KEM-DEM pipeline**
  - Dilithium3 signs the plaintext
  - Payload = `[sig_len][signature][plaintext]`
  - Kyber768 encapsulates a shared secret
  - AES-256-GCM encrypts the payload with the shared secret
- **Three security levels**
  - Level 1: Password-protected (scrypt KDF → AES key)
  - Level 2: Pure PQC (Kyber768 + Dilithium3)
  - Level 3: Hybrid RSA-2048 + Kyber768 (SHA-256 of both secrets)
- **Forward Secrecy Ratchet**
  - Kyber-based DH ratchet (`ratchet_init/advance/dh_step/dh_receive`)
  - Per-recipient `ratchet_states` table tracks chain key + step
  - Each message uses a fresh AES key derived from the ratchet
- **Zero-knowledge-capable key storage**
  - `encrypt_key_blob()` / `decrypt_key_blob()` encrypt private keys using password-derived AES key
  - Blob layout: `[16B salt][12B nonce][16B tag][ciphertext(JSON)]`
  - `encrypted_key_blob` column on `users` enables server-side storage without plaintext keys
- **Encrypted attachments**
  - `encrypt_attachment()` / `decrypt_attachment()` wrap file data in AES-256-GCM
  - `attachments` table stores cipher blob + optional per-file key
  - Download API decrypts transparently
- **Multi-recipient encryption**
  - One AES key for the message body
  - Per-recipient Kyber encapsulation + wrapped AES key
  - Decryptable by each recipient independently

### 3.2 Authentication & Sessions

- **JWT authentication** (`auth.py`)
  - HMAC-SHA256 signed JWTs using `QEC_JWT_SECRET`
  - Access tokens (1h) + refresh tokens (7 days)
  - Refresh endpoint with rotation + blacklist on logout
- **Session tracking**
  - `sessions` table for IP, user-agent, timestamps
  - API to list and revoke active sessions per user
- **Rate limiting & CSRF**
  - `flask-limiter` with configurable limits for auth vs general API
  - Per-session CSRF token checked on mutating endpoints

### 3.3 Email Features

- **Folders**: Inbox, Sent, Drafts, Archive, Trash with unread counts
- **Threading**: `thread_id` + `In-Reply-To` headers allow conversation views
- **Drafts**: Save, update, delete, and list drafts per user
- **Contacts**: Address book with PQC key fingerprints and verification flags
- **Search**: Full-text search on sender, subject, and plaintext
- **Audit log**: Per-user log of logins, sends, tamper demos, etc.

---

## 4. Frontend (React + TypeScript + Tailwind)

The new SPA lives in `frontend/` and mirrors the original Jinja UI but with a modern stack:

- **Tech stack**: React 19, TypeScript, Vite, Tailwind CSS, Zustand, socket.io-client
- **Key components**:
  - `Header` — logo, algorithm chips, user tabs, theme toggle
  - `Sidebar` — folders, unread counts, inbox list, "Check Mail" button
  - `MainPanel` — tabbed content (Compose, Read, Keys, Benchmarks, Audit, Settings, Architecture)
  - `CryptoPanel` — step-by-step cryptographic process log
  - `ComposeForm` — supports all three security levels + encrypted subject
- **State management** (`useStore.ts`):
  - Tracks `appState`, `activeUser`, `activeFolder`, `emails`, `folders`, `cryptoLog`, auth tokens
  - Encapsulates API calls and WebSocket notifications
- **Styling**:
  - Tailwind-based design system using the same color palette as the Jinja template
  - Dark/light theme toggle via CSS variables + `localStorage`

> Dev command: from `frontend/` run `npm install` then `npm run dev`.
> The Vite dev server proxies `/api` and `/socket.io` to the Flask backend on `:5001`.

---

## 5. Infrastructure & Deployment

### 5.1 Docker & Docker Compose

- **Dockerfile**
  - Multi-stage build: compile `liboqs` in a builder image, copy into a slim runtime
  - Installs Python deps via `requirements.txt`
  - Health check hitting `/api/auth/status`
- **docker-compose.yml**
  - `app` service: runs Flask app on port 5001, with configurable `DATABASE_URL`
  - `postgres` service (optional profile): PostgreSQL 16 with persistent volume
  - `nginx` service (optional `tls` profile): TLS 1.3 reverse proxy on 80/443

### 5.2 Nginx TLS Proxy

- `nginx/nginx.conf`:
  - TLS 1.3-only config with HSTS and security headers
  - Separate rate limits for `/api/auth/` vs `/api/`
  - WebSocket support for `/socket.io/`
- `nginx/generate-certs.sh`:
  - Generates self-signed dev certs in `nginx/certs/`

### 5.3 Kubernetes Manifests (`k8s/`)

- `namespace.yaml` — dedicated namespace `schrodinger-mail`
- `deployment.yaml` — app + Postgres Deployments with probes and resource limits
- `service.yaml` — ClusterIP services + PVC for Postgres data + Ingress stub
- `configmap.yaml` / `secret.yaml` — app configuration and secrets (JWT, DB URL)

> These manifests are intended as a starting point; you can convert them into a Helm chart if desired.

---

## 6. Observability

- **Structured logging** (`logging_config.py`)
  - JSON logs including timestamp, logger, message, and optional user/action fields
  - Suppresses verbose Werkzeug/SQLAlchemy logs by default
- **Metrics** (`metrics.py`)
  - In-memory counters (emails sent/received/failed, auth events, attack detections)
  - Histograms for request and crypto operation durations
  - `/metrics` — Prometheus text endpoint
  - `/api/metrics` — JSON metrics for UI or scripts

---

## 7. How to Run (Recommended Dev Flow)

### 7.1 Backend

```bash
# From project root
python3.12 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Optionally run DB migrations (for PostgreSQL)
# alembic upgrade head

python app.py
# → http://127.0.0.1:5001 (Jinja UI)
```

### 7.2 Frontend (React SPA)

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000 (Vite dev server)
# Proxies API calls to http://127.0.0.1:5001
```

---

## 8. Notes & Next Steps

- The original prototype stored private keys server-side; the new zero-knowledge key blob support is a **stepping stone** toward true client-only keys (via WASM PQC in the browser).
- For a production deployment you would:
  - Use **PostgreSQL** with encrypted volumes
  - Terminate **TLS** with real certificates (e.g., cert-manager + Let’s Encrypt)
  - Run behind an ingress controller (the manifests already assume Nginx ingress)
  - Replace in-memory metrics with `prometheus_client` and centralize logs

This file should serve as the **single-page overview** for new contributors, while `README.md`, `EXPLANATION.md`, and `SECURITY.md` provide the deep technical background.
