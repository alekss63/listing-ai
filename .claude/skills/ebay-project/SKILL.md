---
name: ebay-project
description: Resume work on the Claude eBay Listing Assistant — recaps project goal, structure, environment setup, and current status. Use at the start of a new session working in this Ebay folder.
---

# Claude eBay Listing Assistant — Project Recap

AI-powered eBay listing generator. Uses the Claude API to analyze item photos/descriptions and generate eBay listings, with eBay Sandbox integration for posting drafts.

## Current Phase

**Phase 1 — Foundation.** Scaffolding is in place; no application logic (routes, services, models) written yet.

## What's been built so far

- Project folders: `backend/`, `tests/`, `docs/`, `logs/`, `uploads/`, `drafts/`
- Python virtual environment at `.venv`
- `requirements.txt`: fastapi, uvicorn, python-dotenv, pydantic, sqlalchemy, alembic, pytest, anthropic, requests, httpx, pillow, watchdog — all installed
- `backend/app/` structure: `api/`, `core/`, `database/`, `services/`, `models/`, `utils/`
- `backend/app/main.py` — minimal FastAPI app (title "Claude eBay Listing Assistant"), confirmed running via `uvicorn backend.app.main:app` from the `Ebay/` folder (serves `http://127.0.0.1:8000`)
- `backend/app/core/config.py` — loads `.env` via `python-dotenv`, exposes a `Settings`/`settings` object with `PROJECT_NAME`, `EBAY_ENV`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `ANTHROPIC_API_KEY`
- `.env` — populated with eBay Sandbox App ID (Client ID), Cert ID (Client Secret), Dev ID, and an Anthropic API key. **Secrets live only in `.env` — never duplicate them into this skill file or memory.**
- `README.md` — project overview, current phase, features, project location

## Known blockers

- ~~Anthropic API key had insufficient credit balance~~ — **resolved 2026-07-25**. User added prepaid API credits at console.anthropic.com; a live `/v1/messages` call now succeeds.

## Next steps (not yet started)

- Build out `backend/app/api/` routes
- Implement Claude-based image analysis service in `backend/app/services/`
- Implement eBay Sandbox API client (OAuth using `EBAY_CLIENT_ID`/`EBAY_CLIENT_SECRET`/`EBAY_DEV_ID`)
- Define data models in `backend/app/models/`
- Set up database via `backend/app/database/` + Alembic migrations
- Write tests in `tests/`

## Conventions established

- Run the server from the `Ebay/` project root (not from `backend/`): `uvicorn backend.app.main:app`
- Config values are read through `app.core.config.settings`, not `os.getenv` scattered elsewhere
