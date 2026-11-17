# NEXUS — Global Multi-Asset Trading Terminal

A research and **paper-trading** terminal for crypto, US stocks, BIST stocks and indices. Every API response carries the source and freshness (`live | delayed | stale | unavailable`) of its data, so free, delayed feeds are never presented as real-time. **It never sends real-money orders.**

> Paper trading and research only. Nothing here is investment advice.

**Live demo:** https://nexus-terminal-lyart.vercel.app · **API docs:** https://nexus-api-lgut.onrender.com/docs _(free tier: the first request after idle can take ~1 minute)_

**Stack:** Python 3.12 · FastAPI · pandas · Next.js 16 / React 19 · TypeScript · lightweight-charts · Redis (optional) · Supabase (optional) · Docker Compose · GitHub Actions

## Highlights

- **Canonical instrument IDs** (`crypto:binance:btcusdt`, `stock:xnas:aapl`, `stock:xist:thyao`) shared by quotes, alerts, orders, notes and backtests.
- **Provider adapters** with honest freshness: Binance (live crypto, REST + websocket trade/kline/depth with reconnect/backoff and depth-sequence resync) and yfinance (delayed stocks/indices). A Redis quote cache serves stale data when a provider fails.
- **Paper broker:** market, limit, stop, stop-limit, bracket and OCO orders with commission, slippage, buying-power and stale-data guards; fills, cash ledger and audit events.
- **Backtest lab:** MA cross, RSI reversion, breakout, momentum and VWAP reclaim; next-bar-open execution, costs, in/out-of-sample optimisation, walk-forward, overfitting warnings, CAGR / Sharpe / Sortino / Calmar / drawdown / expectancy / profit factor.
- **Research:** valuation and growth fundamentals, financial statements, corporate actions, sourced news, SEC/KAP filings, optional Gemini summary that only uses supplied data (deterministic fallback otherwise).
- **Screener + alerts:** RSI, relative volume, momentum, volatility, trend; saved screens; edge-triggered price/volume/indicator alerts.
- **Portfolio analytics:** multi-currency, missing prices are never counted as zero; volatility, drawdown, VaR, Sharpe, beta, correlation, stress tests.
- **Fail-closed broker layer:** live-money trading is intentionally unsupported; an OKX *demo* bot (`x-simulated-trading: 1` enforced) and a local paper bot are available.
- Dense desktop workspace with command palette, TR/EN switch and a mobile layout.

## Architecture

```
frontend (Next.js)  ──REST/WS──►  backend (FastAPI, /api/v1)
  TerminalWorkspace                 terminal/api.py  (single router)
  lib/terminal-api.ts               ├─ providers.py   Binance / yfinance adapters
                                    ├─ paper.py       paper broker
                                    ├─ backtest_engine.py, screener.py, alerts.py, ...
                                    ├─ cache.py       Redis or in-process quote cache
                                    └─ persistence.py memory | Supabase
```

Identity modes (`backend/terminal/auth.py`):

| Mode | When | Who owns state |
|---|---|---|
| Local | default, no auth header | one shared `local-user` |
| Guest | `ALLOW_GUEST=true`, `Authorization: Guest <id>` | one isolated in-memory account per browser |
| Supabase | `Authorization: Bearer <jwt>` (`REQUIRE_AUTH=true` makes it mandatory) | per-user rows with RLS (`backend/schema_v3.sql`) |

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cd backend && ../.venv/bin/python -m uvicorn main:app --reload --port 8000   # http://localhost:8000/docs
cd frontend && npm ci && npm run dev                                        # http://localhost:3000
```

Everything works without Supabase, Redis or API keys. Copy `backend/.env.example` and `frontend/.env.example` to customise. Full stack: `docker compose up`.

## Tests

```bash
.venv/bin/python -m pytest backend/tests -q      # 52 backend tests
cd frontend && npm test && npm run lint && npm run build
cd frontend && npx playwright test               # e2e (needs `npm run build` first)
```

CI (`.github/workflows/ci.yml`) runs pytest, eslint, vitest and `next build`.

## Deploy (free tier)

1. **API → Render** (Docker, Frankfurt region — Binance rejects some regions with HTTP 451). Create a Blueprint from `render.yaml`, then set `CORS_ORIGINS` to the frontend URL. Public demo defaults: `ALLOW_GUEST=true`, `BOT_CONTROL=false`, `PERSISTENCE=memory`.
2. **Frontend → Vercel**: root directory `frontend`, env `NEXT_PUBLIC_API_URL=https://<your-render-service>.onrender.com`. `NEXT_PUBLIC_*` values are inlined at build time, so redeploy after changing them.
3. **Optional**: `REDIS_URL` (Upstash free) for a shared quote cache; Supabase (`PERSISTENCE=supabase`, run `backend/schema_v3.sql`, set `NEXT_PUBLIC_SUPABASE_*` and `REQUIRE_AUTH=true`) for real accounts.
4. **Free domain**: the `*.vercel.app` URL works as-is; for a nicer name, request `<name>.is-a.dev` via a pull request to the `is-a-dev/register` repository and add it as a custom domain in Vercel.

Free-tier caveats: Render sleeps after ~15 minutes idle (the UI shows a "backend is waking up" banner and the first request takes ~30–60 s); in-memory guest accounts reset on restart; the global OKX bot is disabled on the public demo.

## Known limitations

See `TRADING_BOT_PLAN.md` for the audit of the paper engine (open-order reservations, restart recovery, multi-asset margin) and the bot roadmap.

---

## Türkçe özet

Kripto, ABD hisseleri, BIST hisseleri ve endeksler için araştırma ve paper-trading terminali. Ücretsiz veri kaynaklarının gecikme ve güncellik durumu her API yanıtında açıkça taşınır. Gerçek emir göndermez. Yerel çalıştırma ve test komutları yukarıdadır; API dokümantasyonu `http://localhost:8000/docs` adresindedir.

OKX botu varsayılan olarak yerel paper modunda çalışır (`POST /api/v1/bots/okx-btc-1h/start`). OKX demo hesabı için yalnız **Trade** yetkili bir API anahtarı oluşturun, para çekme yetkisi vermeyin ve anahtarları yalnız backend ortamına (`OKX_API_KEY`, `OKX_API_SECRET`, `OKX_API_PASSPHRASE`) ekleyin; ardından `?mode=okx_demo` ile başlatın. Adaptör `x-simulated-trading: 1` başlığını zorunlu gönderir, gerçek para modunu desteklemez. Günlük özsermaye kaybı %1'e ulaşırsa yeni alışlar durur.
