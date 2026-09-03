"""
Trading Terminal API - Gelişmiş borsa analiz terminali.

Endpoints:
  GET /search?q=thy             -> autocomplete önerileri
  GET /analyze/THYAO            -> tam analiz (varsayılan: günlük)
  GET /analyze/THYAO?timeframe=1w  -> haftalık analiz
  GET /market                   -> piyasa geneli
  GET /sectors                  -> sektörel performans
  GET /watchlist                -> watchlist + skorlar
  DELETE /watchlist/{ticker}    -> watchlist'ten çıkar

Çalıştırma:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000
"""

import csv
import io
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import pipeline

try:
    import sentry_sdk

    if os.environ.get("SENTRY_DSN"):
        sentry_sdk.init(dsn=os.environ["SENTRY_DSN"], traces_sample_rate=0.1)
except ImportError:
    pass

app = FastAPI(
    title="Trading Terminal API",
    version="2.1.0",
    description="BIST analiz terminali — teknik skorlar, portföy, alarmlar, backtest. "
                "İnteraktif doküman: /docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


class HoldingIn(BaseModel):
    ticker: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)


class HoldingOut(BaseModel):
    ticker: str
    quantity: float
    price: float


class AlertIn(BaseModel):
    ticker: str = Field(min_length=1)
    condition: str
    target_value: float

SYMBOLS = json.loads(Path(__file__).parent.joinpath("bist_symbols.json").read_text(encoding="utf-8"))


@app.get("/search")
def search(q: str = Query(min_length=1)):
    q_lower = q.lower()
    seen: set = set()
    matches = []
    for s in SYMBOLS:
        if q_lower in s["ticker"].lower() or q_lower in s["name"].lower() or q_lower in s.get("sector", "").lower():
            ticker = s["ticker"] + ".IS"
            if ticker in seen:
                continue
            seen.add(ticker)
            matches.append({"ticker": ticker, "name": s["name"], "sector": s.get("sector", "")})
        if len(matches) >= 10:
            break
    return {"results": matches}


@app.get("/health")
def health():
    status: dict = {"status": "ok", "supabase": "unknown", "gemini": "unknown"}
    try:
        pipeline.get_supabase()
        status["supabase"] = "ok"
    except RuntimeError as e:
        status["supabase"] = f"error: {e}"
    try:
        pipeline.get_gemini_model()
        status["gemini"] = "ok"
    except RuntimeError as e:
        status["gemini"] = f"error: {e}"
    return status


@app.get("/analyze/{ticker}")
def analyze(ticker: str, refresh: bool = False, timeframe: str = "1d"):
    try:
        return pipeline.analyze(ticker, force_refresh=refresh, timeframe=timeframe)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Portföy güncellenemedi: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analiz sırasında hata: {e}")


@app.get("/market")
def market_overview():
    try:
        return pipeline.get_market_overview()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Piyasa verisi alınırken hata: {e}")


@app.get("/sectors")
def sector_performance():
    try:
        return {"sectors": pipeline.get_sector_performance()}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sektör verisi alınırken hata: {e}")


@app.get("/watchlist")
def get_watchlist():
    try:
        from pipeline import get_supabase

        db = get_supabase()
        watchlist = db.table("watchlist").select("ticker,display_name").execute()
        scores = (
            db.table("scores")
            .select("ticker,technical_score,reasoning,calculated_at")
            .eq("horizon", "short")
            .order("calculated_at", desc=True)
            .limit(200)
            .execute()
        )

        latest_by_ticker = {}
        for row in scores.data:
            if row["ticker"] not in latest_by_ticker:
                latest_by_ticker[row["ticker"]] = row

        result = []
        seen_tickers = set()
        for w in watchlist.data:
            if w["ticker"] in seen_tickers:
                continue
            seen_tickers.add(w["ticker"])
            score = latest_by_ticker.get(w["ticker"])
            result.append({
                "ticker": w["ticker"],
                "display_name": w.get("display_name"),
                "technical_score": score.get("technical_score") if score else None,
                "reasoning": score.get("reasoning") if score else None,
                "calculated_at": score.get("calculated_at") if score else None,
            })

        return {"watchlist": result}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Watchlist alınırken hata: {e}")


@app.delete("/watchlist/{ticker}")
def remove_from_watchlist(ticker: str):
    try:
        from pipeline import get_supabase

        ticker_upper = ticker.upper().strip()
        if not ticker_upper.endswith(".IS"):
            ticker_upper += ".IS"

        get_supabase().table("watchlist").delete().eq("ticker", ticker_upper).execute()
        return {"status": "ok", "removed": ticker_upper}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Watchlist güncellenirken hata: {e}")


# ---------- Portföy ----------

@app.get("/portfolio", tags=["portfolio"])
def portfolio_list():
    import portfolio as pf
    try:
        return {"holdings": pf.list_holdings()}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Portföy alınamadı: {e}")


@app.get("/portfolio/summary", tags=["portfolio"])
def portfolio_summary():
    import portfolio as pf
    try:
        return pf.portfolio_summary()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Portföy özeti alınamadı: {e}")


@app.post("/portfolio", tags=["portfolio"])
def portfolio_add(body: HoldingIn):
    import portfolio as pf
    try:
        return pf.add_holding(body.ticker, body.quantity, body.price)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Portföy güncellenemedi: {e}")


@app.delete("/portfolio/{ticker}", tags=["portfolio"])
def portfolio_remove(ticker: str, quantity: float | None = None):
    import portfolio as pf
    try:
        return pf.remove_holding(ticker, quantity)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Portföy güncellenemedi: {e}")


# ---------- Alarmlar ----------

@app.get("/alerts", tags=["alerts"])
def alerts_list(active_only: bool = False):
    import portfolio as pf
    try:
        return {"alerts": pf.list_alerts(active_only=active_only)}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alarmlar alınamadı: {e}")


@app.post("/alerts", tags=["alerts"])
def alerts_create(body: AlertIn):
    import portfolio as pf
    try:
        return pf.create_alert(body.ticker, body.condition, body.target_value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alarm oluşturulamadı: {e}")


@app.delete("/alerts/{alert_id}", tags=["alerts"])
def alerts_delete(alert_id: int):
    import portfolio as pf
    try:
        pf.delete_alert(alert_id)
        return {"status": "ok", "deleted": alert_id}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alarm silinemedi: {e}")


@app.post("/alerts/check", tags=["alerts"])
def alerts_check():
    import portfolio as pf
    try:
        return pf.check_alerts()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alarm kontrolü başarısız: {e}")


# ---------- Karşılaştırma / Backtest / Haber / Export ----------

@app.get("/compare", tags=["analysis"])
def compare(tickers: str = Query(min_length=3), ai: bool = False):
    import compare as cmp
    try:
        return cmp.compare_tickers([t.strip() for t in tickers.split(",")], with_ai=ai)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Karşılaştırma hatası: {e}")


@app.get("/backtest/{ticker}", tags=["analysis"])
def backtest(ticker: str, strategy: str = "ma_cross", fast: int = 20,
             slow: int = 50, rsi_buy: float = 30.0, rsi_sell: float = 70.0):
    import backtest as bt
    try:
        return bt.run_backtest(ticker, strategy=strategy, fast=fast, slow=slow,
                               rsi_buy=rsi_buy, rsi_sell=rsi_sell)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Portföy güncellenemedi: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest hatası: {e}")


@app.get("/news", tags=["news"])
def market_news(limit: int = 10):
    import news as nw
    return nw.get_market_news(limit=min(limit, 20))


@app.get("/news/{ticker}", tags=["news"])
def ticker_news(ticker: str, limit: int = 8):
    import news as nw
    return nw.get_ticker_news(ticker, limit=min(limit, 20))


@app.get("/export/{ticker}", tags=["export"])
def export_csv(ticker: str, days: int = 365):
    try:
        from pipeline import get_supabase, normalize_ticker
        t = normalize_ticker(ticker)
        res = (
            get_supabase().table("price_history")
            .select("date,open,high,low,close,volume")
            .eq("ticker", t)
            .order("date")
            .execute()
        )
        rows = res.data or []
        if days < 365 * 5:
            rows = rows[-days:]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=["date", "open", "high", "low", "close", "volume"])
        w.writeheader()
        w.writerows(rows)
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={t}.csv"},
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
