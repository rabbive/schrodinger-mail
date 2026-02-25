# AGENTS.md

## Cursor Cloud specific instructions

### Product overview
Schrödinger Mail is a quantum-secure email client using post-quantum cryptography (Kyber768 KEM + Dilithium3 signatures + AES-256-GCM). Flask backend on port 5001, React/Vite frontend on port 3000.

### System dependency: liboqs
The `liboqs` C library **must** be compiled from source before `pip install -r requirements.txt` will work. The update script handles this automatically. If you see `ImportError` from `oqs`, run:
```
git clone --depth 1 https://github.com/open-quantum-safe/liboqs.git /tmp/liboqs
cd /tmp/liboqs && mkdir -p build && cd build && cmake -GNinja .. -DCMAKE_INSTALL_PREFIX=/usr/local -DBUILD_SHARED_LIBS=ON && ninja && sudo ninja install && sudo ldconfig
```

### Running services
- **Backend**: `python3 app.py` — serves on http://127.0.0.1:5001. Uses SQLite by default (zero config).
- **Frontend dev**: `cd frontend && npx vite --host 0.0.0.0 --port 3000` — proxies `/api` and `/socket.io` to the backend.
- Start the backend **before** the frontend (Vite proxies API calls to port 5001).

### Tests and lint
- **Python tests**: `python3 -m pytest tests/ -v` (123 tests)
- **Python lint**: `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=venv,.venv,__pycache__,.git,tests,alembic,frontend,node_modules`
- **TypeScript check**: `cd frontend && npx tsc --noEmit` (2 pre-existing unused-variable warnings)
- **Frontend lint**: `npm run lint` in `frontend/` — note: no `.eslintrc` config file exists in the repo (pre-existing gap), so ESLint v9+ will error.

### Gotchas
- Use `python3` not `python` — the system only has `python3` on PATH.
- `~/.local/bin` must be on PATH for `pytest`, `flake8`, etc. (pip installs there as non-root).
- The liboqs-python version warning (`liboqs version 0.15.0 differs from liboqs-python version 0.14.1`) is harmless and does not affect functionality.
- The database file `quantum_email.db` is auto-created on first run. Delete it to reset state.
