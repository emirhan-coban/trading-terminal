"""Portföy takibi ve fiyat alarm sistemi.

Tablolar (bkz. MIGRATION.sql):
  portfolio: ticker (PK), quantity, avg_cost, updated_at
  alerts: id, ticker, condition, target_value, is_active, last_value,
          triggered_at, created_at
"""

from datetime import datetime
from typing import Optional

from pipeline import get_supabase, normalize_ticker


# ---------- Portföy ----------

def list_holdings() -> list:
    res = get_supabase().table("portfolio").select("*").order("ticker").execute()
    return res.data or []


def add_holding(ticker_raw: str, quantity: float, price: float) -> dict:
    if quantity <= 0 or price <= 0:
        raise ValueError("Adet ve fiyat pozitif olmalı.")
    ticker = normalize_ticker(ticker_raw)
    db = get_supabase()
    existing = db.table("portfolio").select("*").eq("ticker", ticker).execute()

    if existing.data:
        old = existing.data[0]
        new_qty = float(old["quantity"]) + quantity
        new_avg = (float(old["quantity"]) * float(old["avg_cost"]) + quantity * price) / new_qty
        row = {"ticker": ticker, "quantity": new_qty, "avg_cost": new_avg,
               "updated_at": datetime.now().isoformat()}
    else:
        row = {"ticker": ticker, "quantity": quantity, "avg_cost": price,
               "updated_at": datetime.now().isoformat()}

    db.table("portfolio").upsert([row], on_conflict="ticker").execute()
    return row


def remove_holding(ticker_raw: str, quantity: Optional[float] = None) -> dict:
    ticker = normalize_ticker(ticker_raw)
    db = get_supabase()
    existing = db.table("portfolio").select("*").eq("ticker", ticker).execute()
    if not existing.data:
        raise ValueError(f"{ticker} portföyde yok.")

    old = existing.data[0]
    if quantity is None or quantity >= float(old["quantity"]):
        db.table("portfolio").delete().eq("ticker", ticker).execute()
        return {"ticker": ticker, "removed": True, "remaining": 0}

    new_qty = float(old["quantity"]) - quantity
    db.table("portfolio").update(
        {"quantity": new_qty, "updated_at": datetime.now().isoformat()}
    ).eq("ticker", ticker).execute()
    return {"ticker": ticker, "removed": False, "remaining": new_qty}


def _latest_closes(tickers: list) -> dict:
    if not tickers:
        return {}
    res = (
        get_supabase().table("price_history")
        .select("ticker,close,date")
        .in_("ticker", tickers)
        .order("date", desc=True)
        .limit(len(tickers) * 3)
        .execute()
    )
    closes = {}
    for row in res.data or []:
        if row["ticker"] not in closes and row.get("close") is not None:
            closes[row["ticker"]] = float(row["close"])
    return closes


def portfolio_summary() -> dict:
    holdings = list_holdings()
    closes = _latest_closes([h["ticker"] for h in holdings])

    positions = []
    total_cost = 0.0
    total_value = 0.0
    for h in holdings:
        qty = float(h["quantity"])
        avg = float(h["avg_cost"])
        cost = qty * avg
        last = closes.get(h["ticker"])
        value = qty * last if last is not None else None
        pnl = (value - cost) if value is not None else None
        total_cost += cost
        if value is not None:
            total_value += value
        positions.append({
            "ticker": h["ticker"],
            "quantity": qty,
            "avg_cost": round(avg, 2),
            "last_price": round(last, 2) if last is not None else None,
            "cost": round(cost, 2),
            "market_value": round(value, 2) if value is not None else None,
            "pnl": round(pnl, 2) if pnl is not None else None,
            "pnl_pct": round(pnl / cost * 100, 2) if pnl is not None and cost else None,
        })

    total_pnl = total_value - total_cost if positions else 0.0
    return {
        "positions": positions,
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl / total_cost * 100, 2) if total_cost else 0.0,
        "updated_at": datetime.now().isoformat(),
    }


# ---------- Alarmlar ----------

CONDITIONS = ("price_above", "price_below", "rsi_above", "rsi_below",
              "score_above", "score_below")


def list_alerts(active_only: bool = False) -> list:
    q = get_supabase().table("alerts").select("*").order("created_at", desc=True)
    if active_only:
        q = q.eq("is_active", True)
    res = q.execute()
    return res.data or []


def create_alert(ticker_raw: str, condition: str, target_value: float) -> dict:
    if condition not in CONDITIONS:
        raise ValueError(f"Geçersiz koşul. İzin verilenler: {', '.join(CONDITIONS)}")
    ticker = normalize_ticker(ticker_raw)
    row = {
        "ticker": ticker,
        "condition": condition,
        "target_value": float(target_value),
        "is_active": True,
        "created_at": datetime.now().isoformat(),
    }
    res = get_supabase().table("alerts").insert(row).execute()
    return (res.data or [row])[0]


def delete_alert(alert_id: int) -> None:
    get_supabase().table("alerts").delete().eq("id", alert_id).execute()


def _latest_signal(ticker: str) -> dict:
    """Alarm değerlendirmesi için son fiyat + RSI + skor."""
    db = get_supabase()
    price = db.table("price_history").select("close").eq("ticker", ticker) \
        .order("date", desc=True).limit(1).execute()
    score = db.table("scores").select("technical_score,indicators") \
        .eq("ticker", ticker).order("calculated_at", desc=True).limit(1).execute()

    out: dict = {"close": None, "rsi": None, "score": None}
    if price.data and price.data[0].get("close") is not None:
        out["close"] = float(price.data[0]["close"])
    if score.data:
        if score.data[0].get("technical_score") is not None:
            out["score"] = float(score.data[0]["technical_score"])
        try:
            import json as _json
            ind = score.data[0].get("indicators")
            ind = _json.loads(ind) if isinstance(ind, str) else (ind or {})
            if ind.get("rsi") is not None:
                out["rsi"] = float(ind["rsi"])
        except Exception:
            pass
    return out


def _evaluate(condition: str, target: float, sig: dict) -> tuple:
    """(tetiklendi_mi, güncel_değer) döner."""
    mapping = {
        "price_above": ("close", lambda v: v is not None and v > target),
        "price_below": ("close", lambda v: v is not None and v < target),
        "rsi_above": ("rsi", lambda v: v is not None and v > target),
        "rsi_below": ("rsi", lambda v: v is not None and v < target),
        "score_above": ("score", lambda v: v is not None and v > target),
        "score_below": ("score", lambda v: v is not None and v < target),
    }
    key, fn = mapping[condition]
    value = sig.get(key)
    return (bool(fn(value)), value)


def check_alerts() -> dict:
    """Aktif alarmları değerlendirir; tetiklenenleri tek-seferlik kapatır."""
    db = get_supabase()
    triggered = []
    checked = 0
    for alert in list_alerts(active_only=True):
        checked += 1
        sig = _latest_signal(alert["ticker"])
        hit, value = _evaluate(alert["condition"], float(alert["target_value"]), sig)
        update = {"last_value": value}
        if hit:
            update["is_active"] = False
            update["triggered_at"] = datetime.now().isoformat()
            triggered.append({**alert, **update})
        db.table("alerts").update(update).eq("id", alert["id"]).execute()

    return {"checked": checked, "triggered": triggered,
            "triggered_count": len(triggered)}
