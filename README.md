# Borsa Terminali — BIST Analiz Terminali v2.1

Bloomberg / Midas Atlas / Fintables tarzı kişisel BIST terminali:
teknik skorlar, AI analist yorumları, portföy takibi, alarmlar,
hisse karşılaştırma, backtest, haber akışı.

## Mimari

```
trading-terminal/
├── backend/            # FastAPI (Python 3.12, .venv)
│   ├── main.py         # API endpoint'leri (/docs → OpenAPI)
│   ├── pipeline.py     # Analiz hattı: fiyat + temel + teknik + AI
│   ├── portfolio.py    # Portföy + alarm işlemleri
│   ├── backtest.py     # MA-kesişim / RSI stratejileri
│   ├── compare.py      # Hisse karşılaştırma (+opsiyonel AI)
│   ├── news.py         # Google News RSS (anahtarsız)
│   ├── bist_symbols.json  # 330 hisse + sektör
│   └── tests/          # pytest (14 test)
├── frontend/           # Next.js 16 + Tailwind v4 (vitest: 10 test)
├── requirements.txt / requirements-dev.txt
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Kurulum

```bash
# 1) Python 3.12 (macOS): brew install python@3.12
/opt/homebrew/bin/python3.12 -m venv .venv
./.venv/bin/pip install -r requirements-dev.txt

# 2) Supabase SQL Editor'da backend/MIGRATION.sql'i çalıştır
#    (tablolar: watchlist, price_history, financials, scores +
#     portfolio, alerts + yeni kolonlar)

# 3) backend/.env  (bkz. backend/.env.example)
# 4) frontend/.env.local  (bkz. frontend/.env.example — anon public anahtar)

# 5) Çalıştır
cd backend && ../.venv/bin/python -m uvicorn main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

## API (http://localhost:8000/docs)

| Endpoint | Açıklama |
|---|---|
| `GET /search?q=` | Hisse arama (autocomplete) |
| `GET /analyze/{ticker}?timeframe=1d&refresh=` | Tam analiz + AI yorumu |
| `GET /market`, `GET /sectors` | Piyasa geneli, sektör skorları |
| `GET/POST/DELETE /portfolio…` | Portföy + K/Z özeti |
| `GET/POST/DELETE /alerts…`, `POST /alerts/check` | Fiyat/RSI/skor alarmları |
| `GET /compare?tickers=A,B&ai=` | Yan yana karşılaştırma |
| `GET /backtest/{ticker}?strategy=` | `ma_cross` / `rsi` backtest |
| `GET /news`, `GET /news/{ticker}` | Haber başlıkları (RSS) |
| `GET /export/{ticker}` | Fiyat geçmişi CSV |
| `GET /health` | Supabase/Gemini durum kontrolü |

## Testler

```bash
./.venv/bin/python -m pytest backend/tests/ -q   # 14 test
cd frontend && npx vitest run                     # 10 test
```

## Notlar

- `SENTRY_DSN` tanımlıysa backend hataları Sentry'ye gider (opsiyonel).
- Auth: Supabase e-posta girişi (`/login`); veri tek kullanıcılı modda globaldir.
- PDF export yok — CSV + tarayıcı yazdırma önerilir.
