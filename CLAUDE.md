# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

NEXUS: research + **paper-trading** terminal for crypto, US stocks, BIST stocks and indices (FastAPI backend, Next.js frontend). It never sends real-money orders; `terminal/brokers.py` keeps live trading fail-closed. README and comments are mostly Turkish. `frontend/CLAUDE.md` → `frontend/AGENTS.md` warns that this Next.js (16.x, React 19) differs from older versions: read the relevant guide in `frontend/node_modules/next/dist/docs/` before writing Next-specific code.

## Commands

Backend (Python 3.12; a `.venv` at the repo root is assumed by the README):
- Install: `pip install -r requirements-dev.txt`
- Run API: `cd backend && python -m uvicorn main:app --reload --port 8000` (docs at `/docs`)
- Tests (CI command, run from repo root; `pytest.ini` sets `pythonpath=backend`): `python -m pytest backend/tests -q`
- Single test: `python -m pytest backend/tests/test_paper_advanced.py::test_name -q`
- Quote worker (separate process, needs Redis): `cd backend && python -m terminal.worker`

Frontend (`cd frontend`; Node 20):
- `npm run dev`, `npm run lint`, `npm test` (vitest), `npx vitest run lib/utils.test.ts` (single file), `npm run test:e2e` (Playwright, `e2e/terminal.spec.ts`)
- `npm run build` uses `next build --webpack`.

Full stack: `docker compose up` (redis, backend, worker, frontend). Needs `backend/.env` (copy `backend/.env.example`) and `frontend/.env.local`. The frontend reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

## Architecture

**Backend (`backend/`)**: `main.py` (FastAPI app, CORS from `CORS_ORIGINS`, `x-correlation-id` middleware, `/health`) plus the `terminal/` package. `terminal/api.py` is the single router (`/api/v1`) that wires every module together: instruments/market, screener, alerts, paper trading, research/journal, backtests, portfolio, workspaces, bots, provider health, and a websocket quote stream. Modules are mostly module-level singletons (`catalog`, `providers`, `paper_broker`, `alerts`, `quote_cache`, `repository`, `bot_service`, ...) imported by `api.py`. The code style is deliberately dense (1-space indent, semicolons); match the surrounding file. `schema_v3.sql` is the Supabase schema (RLS, per-user isolation). The old BIST v2 modules were removed.

Key concepts that span files:
- **Canonical `instrument_id`** (`crypto:binance:btcusdt`, `stock:xnas:aapl`, `stock:xist:thyao`) resolved through `catalog.py`; all APIs, alerts, paper orders and notes key off it.
- **Response envelope + freshness**: API responses are `{data, meta}` where `meta.freshness` is `live|delayed|stale|unavailable` (models in `models.py`, mirrored by `Envelope<T>` in `frontend/lib/terminal-api.ts`). Free data sources are Binance (live crypto) and yfinance (delayed stocks); paper orders are rejected on stale data. Keep freshness/source honest when adding endpoints.
- **Persistence** (`persistence.py`): `PERSISTENCE=memory` (default, dependency-free) or `supabase`. When disabled every repository call is a no-op/`None`, so most state is in-process memory. Bot state is separate: local SQLite at `BOT_DB_PATH` (resumed on startup via `bot_service.resume()`).
- **Auth** (`auth.py`): three identity modes. No header → shared `local-user`; `Authorization: Guest <id>` with `ALLOW_GUEST=true` → isolated in-memory account per browser (the frontend generates the id, see `accessToken()` in `lib/terminal-api.ts`; websocket passes `?token=guest:<id>`); Supabase `Bearer` JWT, mandatory with `REQUIRE_AUTH=true`. Guests are in-memory only, so don't combine them with `PERSISTENCE=supabase` (user_id columns are UUIDs). Bot start/stop go through `bot_control()` and are refused for guests or when `BOT_CONTROL=false`.
- **Quote cache** (`cache.py`, `worker.py`): Redis cache with stale fallback when a provider fails; the worker refreshes quotes every 15s.
- **Bot** (`bot.py`, `okx_broker.py`): the `okx-btc-1h` bot runs as a backend background task in local paper mode or `mode=okx_demo` (OKX demo, forced `x-simulated-trading: 1`; real-money mode is intentionally unsupported). `TRADING_BOT_PLAN.md` documents known paper-engine/backtest correctness gaps and the roadmap.

**Frontend (`frontend/`)**: Next.js App Router. `/` renders `components/TerminalWorkspace.tsx` (the dense workspace; styles in `app/terminal.css`), `/multichart` the synchronized charts, `/bot` the simple bot dashboard (styles in `app/bot/bot.css`; keep the two stylesheets separate, they define conflicting `:root` vars). `lib/terminal-api.ts` is the typed API client; `lib/supabase.ts` uses placeholder env values so the app runs without Supabase (guest mode). `BackendStatus` shows a banner while a sleeping free-tier API wakes up. `app/api/search/route.ts` is the only Next route handler.

Deployment: `render.yaml` (API, Docker, Frankfurt) + Vercel for `frontend/`; see README. `NEXT_PUBLIC_*` are inlined at build time.

CI (`.github/workflows/ci.yml`): backend pytest; frontend `eslint .`, `vitest run`, `next build`.
