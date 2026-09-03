"""Hisse karşılaştırma — teknik skor + göstergeler + rasyolar yan yana."""

import json as _json

from pipeline import (get_supabase, normalize_ticker, get_latest_financials,
                      get_gemini_model)


def _latest_score(ticker: str) -> dict:
    res = (
        get_supabase().table("scores")
        .select("technical_score,indicators,reasoning,calculated_at")
        .eq("ticker", ticker)
        .eq("horizon", "short")
        .order("calculated_at", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        return {}
    row = res.data[0]
    ind = row.get("indicators")
    try:
        row["indicators"] = _json.loads(ind) if isinstance(ind, str) else (ind or {})
    except Exception:
        row["indicators"] = {}
    return row


def _latest_price(ticker: str) -> dict:
    res = (
        get_supabase().table("price_history")
        .select("close,date")
        .eq("ticker", ticker)
        .order("date", desc=True)
        .limit(2)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return {}
    out = {"close": rows[0].get("close")}
    if len(rows) > 1 and rows[1].get("close"):
        prev = rows[1]["close"]
        out["change_pct"] = round((rows[0]["close"] - prev) / prev * 100, 2)
    return out


def compare_tickers(raw_tickers: list, with_ai: bool = False) -> dict:
    tickers = [normalize_ticker(t) for t in raw_tickers if t and t.strip()]
    tickers = list(dict.fromkeys(tickers))[:4]
    if len(tickers) < 2:
        raise ValueError("Karşılaştırma için en az 2 hisse gerekli (en fazla 4).")

    rows = []
    for t in tickers:
        score = _latest_score(t)
        rows.append({
            "ticker": t,
            "technical_score": score.get("technical_score"),
            "indicators": score.get("indicators", {}),
            "financials": get_latest_financials(t),
            "price": _latest_price(t),
            "calculated_at": score.get("calculated_at"),
        })

    result: dict = {"tickers": tickers, "rows": rows}

    if with_ai:
        brief = [{k: r[k] for k in ("ticker", "technical_score", "financials", "price")} for r in rows]
        prompt = (f"Aşağıdaki BIST hisselerini teknik skor, fiyat hareketi ve "
                  f"rasyolar açısından 4-5 cümlede karşılaştır. Kesin AL/SAT deme, "
                  f"Türkçe yaz, gözlemsel analiz olduğunu belirt.\n{_json.dumps(brief, default=str)}")
        result["ai_comparison"] = get_gemini_model().generate_content(prompt).text.strip()

    return result
