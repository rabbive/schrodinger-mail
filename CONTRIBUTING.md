# Contributing to Schrödinger Mail

Thanks for your interest in contributing. This project focuses on post-quantum secure messaging, so changes should prioritize correctness, security, and clarity.

## Ways to contribute

- Report bugs and edge cases
- Improve docs and architecture explanations
- Add tests for crypto, API, and database behavior
- Improve frontend usability and accessibility
- Propose security hardening ideas backed by rationale

## Development setup

1. Fork the repository and create a feature branch:
   - `git checkout -b feat/short-description`
2. Set up backend:
   - `python -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
3. Set up frontend:
   - `cd frontend`
   - `npm install`
4. Run the app:
   - Backend: `python app.py`
   - Frontend (optional): `npm run dev`

## Pull request checklist

Before opening a PR, please ensure:

- Changes are focused and documented
- Existing tests pass: `pytest tests/ -v`
- New behavior includes tests when practical
- No secrets or credentials are committed
- API or UX changes are reflected in docs

## Coding guidelines

- Keep changes small and reviewable
- Prefer explicit, readable code over clever abstractions
- Preserve backwards compatibility when possible
- For security-sensitive code, include notes on threat impact and assumptions
- Add/adjust tests whenever logic changes

## Commit message style

Use concise, intent-first messages. Examples:

- `feat: add encrypted attachment metadata validation`
- `fix: reject malformed KEM payload during receive`
- `docs: clarify threat model limitations`

## Reporting security issues

Do not open public issues for suspected vulnerabilities. Please use the private process in `SECURITY_CONTACT.md`.
