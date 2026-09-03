"""
Gelişmiş trading terminali backend pipeline'ı.
Teknik göstergeler: RSI, MACD, SMA, EMA, ATR, Bollinger Bands, Stochastic, VWAP, OBV, CCI, Williams %R, ADX
Multi-timeframe analiz, temettü verisi, sektör analizi, piyasa geneli.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import numpy as np
import yfinance as yf
from ta.momentum import RSIIndicator, StochRSIIndicator, WilliamsRIndicator
from ta.trend import MACD, SMAIndicator, EMAIndicator, ADXIndicator, CCIIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")
load_dotenv()

FRESHNESS_WINDOW = timedelta(hours=4)

_supabase_client: Optional[Client] = None
_supabase_error: Optional[str] = None
_gemini_model = None


def get_supabase() -> Client:
    """Lazy Supabase client — import anında patlamaz, eksik/geçersiz
    anahtarda anlamlı hata verir. supabase-py 2.5.x eski JWT formatını
    bekler; yeni `sb_secret_...` anahtarları bu sürümde reddedilir."""
    global _supabase_client, _supabase_error
    if _supabase_client is not None:
        return _supabase_client
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_KEY", "").strip()
    if not url or not key:
        _supabase_error = "SUPABASE_URL / SUPABASE_KEY .env'de tanımlı değil."
        raise RuntimeError(_supabase_error)
    try:
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception as e:
        _supabase_error = (
            f"Supabase bağlantısı kurulamadı: {e}. "
            "Not: supabase-py 2.5.x yeni `sb_secret_...` anahtarları kabul etmez; "
            "Dashboard → Settings → API → Legacy API keys altındaki `service_role` "
            "JWT anahtarını kullanın ya da Python 3.10+ ile supabase>=2.31 kurun."
        )
        raise RuntimeError(_supabase_error)


def get_gemini_model():
    """Lazy Gemini modeli — anahtar yoksa sadece analyze çağrısında hata verir."""
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model
    import google.generativeai as genai
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY .env'de tanımlı değil.")
    genai.configure(api_key=api_key)
    _gemini_model = genai.GenerativeModel("gemini-2.5-flash")
    return _gemini_model

import math

def clean_nan(obj):
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    return obj


# DB'deki scores_horizon_check constraint'i eski değerleri bekler
TIMEFRAME_TO_HORIZON = {"1d": "short", "1w": "medium", "1M": "long"}


def _db_horizon(timeframe: str) -> str:
    return TIMEFRAME_TO_HORIZON.get(timeframe, "short")


def _num(value) -> Optional[float]:
    """yfinance NaN/inf değerlerini None'a çevirir (Supabase JSON hatası önler)."""
    import math
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def normalize_ticker(raw: str) -> str:
    raw = raw.strip().upper()
    return raw if raw.endswith(".IS") else f"{raw}.IS"


def ensure_in_watchlist(ticker: str, display_name: str = None) -> None:
    db = get_supabase()
    existing = db.table("watchlist").select("ticker").eq("ticker", ticker).execute()
    if not existing.data:
        name = display_name or ticker.replace(".IS", "")
        try:
            db.table("watchlist").insert({"ticker": ticker, "display_name": name}).execute()
        except Exception as e:
            # Yarış durumu: araya başka istek girdiyse (23505/409) sessiz geç
            if "23505" not in str(e) and "409" not in str(e) and "duplicate" not in str(e).lower():
                raise


def fetch_price(ticker: str, days: int = 365) -> None:
    end = datetime.now()
    start = end - timedelta(days=days)
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)

    if df.empty:
        raise ValueError(f"{ticker} için fiyat verisi bulunamadı.")

    # yfinance 1.x tek ticker'da bile MultiIndex kolon döner — düzleştir
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    rows = []
    for date, row in df.iterrows():
        try:
            o, h, l, c = row["Open"], row["High"], row["Low"], row["Close"]
            if pd.isna(o) or pd.isna(h) or pd.isna(l) or pd.isna(c):
                continue
            volume = row["Volume"]
            volume = 0 if pd.isna(volume) else int(float(volume))
            rows.append({
                "ticker": ticker,
                "date": date.strftime("%Y-%m-%d"),
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
                "volume": volume,
            })
        except (ValueError, TypeError):
            continue

    if not rows:
        raise ValueError(f"{ticker} için işlenebilir fiyat verisi yok.")

    if rows:
        get_supabase().table("price_history").upsert(rows, on_conflict="ticker,date").execute()


def fetch_financials(ticker: str) -> None:
    ticker_bare = ticker.replace(".IS", "")
    period = f"{datetime.now().year}-Q{(datetime.now().month - 1) // 3 + 1}"

    info = yf.Ticker(ticker).info
    trailing_pe = info.get("trailingPE")
    forward_pe = info.get("forwardPE")

    if trailing_pe is not None:
        pe_ratio, pe_source = trailing_pe, "trailing"
    elif forward_pe is not None:
        pe_ratio, pe_source = forward_pe, "forward"
    else:
        pe_ratio, pe_source = None, "unavailable"

    try:
        comp = yf.Ticker(ticker)
        dividends = comp.dividends
        if len(dividends) > 0:
            last_year_dividends = dividends[dividends.index >= datetime.now() - timedelta(days=365)]
            annual_dividend = float(last_year_dividends.sum())
            current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            dividend_yield = annual_dividend / current_price if current_price > 0 else None
        else:
            dividend_yield = None
    except Exception:
        dividend_yield = None

    row = {
        "ticker": ticker,
        "period": period,
        "pe_ratio": _num(pe_ratio),
        "pb_ratio": _num(info.get("priceToBook")),
        "debt_to_equity": _num(info.get("debtToEquity")),
        "revenue_growth": _num(info.get("revenueGrowth")),
        "dividend_yield": _num(dividend_yield),
        "market_cap": _num(info.get("marketCap")),
        "raw_data": json.dumps({
            "ratio_meta": {"pe_source": pe_source, "trailing_eps": _num(info.get("trailingEps"))},
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "fifty_two_week_high": _num(info.get("fiftyTwoWeekHigh")),
            "fifty_two_week_low": _num(info.get("fiftyTwoWeekLow")),
        }, default=str),
    }
    try:
        get_supabase().table("financials").upsert([row], on_conflict="ticker,period").execute()
    except Exception as e:
        # Eski şemada dividend_yield/market_cap kolonu yoksa
        # (PGRST204 / 42703), temel kolonlarla tekrar dene.
        # Tam şema için MIGRATION.sql'e bak.
        if "PGRST204" in str(e) or "42703" in str(e) or "does not exist" in str(e):
            base_row = {k: row[k] for k in ("ticker", "period", "pe_ratio", "pb_ratio", "debt_to_equity", "revenue_growth", "raw_data")}
            get_supabase().table("financials").upsert([base_row], on_conflict="ticker,period").execute()
        else:
            raise


def compute_technical(ticker: str, timeframe: str = "1d") -> dict:
    days_map = {"1d": 365, "1w": 730, "1M": 1095}
    days = days_map.get(timeframe, 365)

    end = datetime.now()
    start = end - timedelta(days=days)
    df = yf.download(ticker, start=start, end=end, interval=timeframe, progress=False, auto_adjust=False)

    if df.empty or len(df) < 26:
        raise ValueError(f"{ticker} için yeterli fiyat geçmişi yok ({timeframe} timeframe).")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Eksik bar'ları (bugünkü işlem görmemiş gün vb.) temizle,
    # yoksa son satır NaN olur ve göstergeler boş döner.
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if df.empty or len(df) < 26:
        raise ValueError(f"{ticker} için yeterli fiyat geçmişi yok ({timeframe} timeframe).")
    df["Volume"] = df["Volume"].fillna(0)

    df["rsi"] = RSIIndicator(close=df["Close"], window=14).rsi()

    macd_calc = MACD(close=df["Close"])
    df["macd"] = macd_calc.macd()
    df["macd_signal"] = macd_calc.macd_signal()
    df["macd_hist"] = macd_calc.macd_diff()

    df["sma20"] = SMAIndicator(close=df["Close"], window=20).sma_indicator()
    df["sma50"] = SMAIndicator(close=df["Close"], window=50).sma_indicator()
    df["sma200"] = SMAIndicator(close=df["Close"], window=200).sma_indicator()
    df["ema20"] = EMAIndicator(close=df["Close"], window=20).ema_indicator()
    df["ema50"] = EMAIndicator(close=df["Close"], window=50).ema_indicator()

    df["atr"] = AverageTrueRange(high=df["High"], low=df["Low"], close=df["Close"], window=14).average_true_range()

    bb = BollingerBands(close=df["Close"], window=20, window_dev=2)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_middle"] = bb.bollinger_mavg()
    df["bb_lower"] = bb.bollinger_lband()
    df["bb_width"] = bb.bollinger_wband()

    stoch = WilliamsRIndicator(high=df["High"], low=df["Low"], close=df["Close"], lbp=14)
    df["williams_r"] = stoch.williams_r()

    df["adx"] = ADXIndicator(high=df["High"], low=df["Low"], close=df["Close"], window=14).adx()
    df["cci"] = CCIIndicator(high=df["High"], low=df["Low"], close=df["Close"], window=20).cci()

    df["obv"] = OnBalanceVolumeIndicator(close=df["Close"], volume=df["Volume"]).on_balance_volume()

    df["vwap"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum() / df["Volume"].cumsum()

    stoch_calc = MACD(close=df["Close"])
    k_period = 14
    low_min = df["Low"].rolling(window=k_period).min()
    high_max = df["High"].rolling(window=k_period).max()
    df["stoch_k"] = 100 * (df["Close"] - low_min) / (high_max - low_min)
    df["stoch_d"] = df["stoch_k"].rolling(window=3).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last

    indicators = {
        "rsi": round(float(last["rsi"]), 2) if pd.notna(last["rsi"]) else None,
        "macd": round(float(last["macd"]), 4) if pd.notna(last["macd"]) else None,
        "macd_signal": round(float(last["macd_signal"]), 4) if pd.notna(last["macd_signal"]) else None,
        "macd_hist": round(float(last["macd_hist"]), 4) if pd.notna(last["macd_hist"]) else None,
        "sma20": round(float(last["sma20"]), 2) if pd.notna(last["sma20"]) else None,
        "sma50": round(float(last["sma50"]), 2) if pd.notna(last["sma50"]) else None,
        "sma200": round(float(last["sma200"]), 2) if pd.notna(last["sma200"]) else None,
        "ema20": round(float(last["ema20"]), 2) if pd.notna(last["ema20"]) else None,
        "ema50": round(float(last["ema50"]), 2) if pd.notna(last["ema50"]) else None,
        "atr": round(float(last["atr"]), 2) if pd.notna(last["atr"]) else None,
        "bb_upper": round(float(last["bb_upper"]), 2) if pd.notna(last["bb_upper"]) else None,
        "bb_middle": round(float(last["bb_middle"]), 2) if pd.notna(last["bb_middle"]) else None,
        "bb_lower": round(float(last["bb_lower"]), 2) if pd.notna(last["bb_lower"]) else None,
        "bb_width": round(float(last["bb_width"]), 4) if pd.notna(last["bb_width"]) else None,
        "williams_r": round(float(last["williams_r"]), 2) if pd.notna(last["williams_r"]) else None,
        "adx": round(float(last["adx"]), 2) if pd.notna(last["adx"]) else None,
        "cci": round(float(last["cci"]), 2) if pd.notna(last["cci"]) else None,
        "obv": round(float(last["obv"]), 0) if pd.notna(last["obv"]) else None,
        "vwap": round(float(last["vwap"]), 2) if pd.notna(last["vwap"]) else None,
        "stoch_k": round(float(last["stoch_k"]), 2) if pd.notna(last["stoch_k"]) else None,
        "stoch_d": round(float(last["stoch_d"]), 2) if pd.notna(last["stoch_d"]) else None,
        "close": round(float(last["Close"]), 2) if pd.notna(last["Close"]) else None,
        "prev_close": round(float(prev["Close"]), 2) if pd.notna(prev["Close"]) else None,
    }

    technical_score = compute_score(indicators)

    return {"indicators": indicators, "technical_score": technical_score, "timeframe": timeframe}


def compute_score(indicators: dict) -> float:
    """Göstergelerden -100..+100 bileşik skor üretir (saf fonksiyon)."""
    score = 0
    if indicators.get("rsi") is not None:
        score += (indicators["rsi"] - 50) * 1.2
    if indicators.get("macd_hist") is not None:
        score += 25 if indicators["macd_hist"] > 0 else -25
    if indicators.get("sma20") is not None and indicators.get("close") is not None:
        score += 15 if indicators["close"] > indicators["sma20"] else -15
    if indicators.get("sma50") is not None and indicators.get("close") is not None:
        score += 10 if indicators["close"] > indicators["sma50"] else -10
    if indicators.get("adx") is not None:
        if indicators["adx"] > 25:
            if indicators.get("close") and indicators.get("sma20") and indicators["close"] > indicators["sma20"]:
                score += 10
            else:
                score -= 10
    if indicators.get("cci") is not None:
        if indicators["cci"] > 100:
            score += 5
        elif indicators["cci"] < -100:
            score -= 5
    if indicators.get("williams_r") is not None:
        if indicators["williams_r"] > -20:
            score -= 5
        elif indicators["williams_r"] < -80:
            score += 5

    return round(max(-100, min(100, score)), 2)


def generate_reasoning(ticker: str, indicators: dict, technical_score: float, ratios: Optional[dict]) -> str:
    prompt = f"""Sen deneyimli bir finansal analistsin. Aşağıdaki teknik ve
fundamental verilere bakarak {ticker} hissesi için 3-4 cümlelik, gerekçeli bir
değerlendirme yaz. Kesin "AL" ya da "SAT" deme, hangi göstergenin ne yöne
işaret ettiğini ve çelişkili sinyalleri açıkça belirt. Türkçe yaz, yatırım
tavsiyesi değil, gözlemsel bir analiz olduğunu unutma.

Teknik göstergeler: {json.dumps(indicators)}
Teknik skor: {technical_score}
Fundamental rasyolar: {json.dumps(ratios) if ratios else "veri yok"}
"""
    response = get_gemini_model().generate_content(prompt)
    return response.text.strip()


def get_latest_financials(ticker: str) -> Optional[dict]:
    try:
        res = (
            get_supabase().table("financials")
            .select("pe_ratio,pb_ratio,debt_to_equity,revenue_growth,dividend_yield,market_cap")
            .eq("ticker", ticker)
            .order("period", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as e:
        if "PGRST204" not in str(e) and "42703" not in str(e) and "does not exist" not in str(e):
            raise
        res = (
            get_supabase().table("financials")
            .select("pe_ratio,pb_ratio,debt_to_equity,revenue_growth")
            .eq("ticker", ticker)
            .order("period", desc=True)
            .limit(1)
            .execute()
        )
    return res.data[0] if res.data else None


def get_fresh_score(ticker: str, timeframe: str = "1d") -> Optional[dict]:
    res = (
        get_supabase().table("scores")
        .select("id,technical_score,indicators,reasoning,calculated_at")
        .eq("ticker", ticker)
        .eq("horizon", _db_horizon(timeframe))
        .order("calculated_at", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None

    row = res.data[0]
    calculated_at = datetime.fromisoformat(row["calculated_at"].replace("Z", "+00:00"))
    age = datetime.now(calculated_at.tzinfo) - calculated_at
    return row if age < FRESHNESS_WINDOW else None


def get_sector_info(ticker: str) -> Optional[dict]:
    ticker_bare = ticker.replace(".IS", "")
    try:
        info = yf.Ticker(ticker).info
        return {
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
        }
    except Exception:
        return None


def analyze(ticker_raw: str, force_refresh: bool = False, timeframe: str = "1d") -> dict:
    ticker = normalize_ticker(ticker_raw)

    if not force_refresh:
        cached = get_fresh_score(ticker, timeframe)
        if cached is not None:
            return clean_nan({"ticker": ticker, "cached": True, "timeframe": timeframe, **cached})

    ensure_in_watchlist(ticker)
    fetch_price(ticker)
    fetch_financials(ticker)

    tech = compute_technical(ticker, timeframe)
    ratios = get_latest_financials(ticker)
    reasoning = generate_reasoning(ticker, tech["indicators"], tech["technical_score"], ratios)

    row = {
        "ticker": ticker,
        "horizon": _db_horizon(timeframe),
        "technical_score": tech["technical_score"],
        "indicators": json.dumps(clean_nan(tech["indicators"])),
        "reasoning": reasoning,
    }
    get_supabase().table("scores").insert(row).execute()

    return clean_nan({"ticker": ticker, "cached": False, "timeframe": timeframe, **row, "indicators": tech["indicators"]})


def get_market_overview() -> dict:
    indices = [
        {"ticker": "XU100.IS", "name": "BIST 100"},
        {"ticker": "XU30.IS", "name": "BIST 30"},
        {"ticker": "XULAS.IS", "name": "BIST Sınai"},
        {"ticker": "XUFIN.IS", "name": "BIST Bankacılık"},
    ]

    index_data = []
    for idx in indices:
        try:
            ticker_obj = yf.Ticker(idx["ticker"])
            hist = ticker_obj.history(period="2d")
            if len(hist) >= 2:
                current = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                change_pct = ((current - prev) / prev) * 100
                index_data.append({
                    "name": idx["name"],
                    "value": round(current, 2),
                    "change_pct": round(change_pct, 2),
                })
            elif len(hist) == 1:
                index_data.append({
                    "name": idx["name"],
                    "value": round(float(hist["Close"].iloc[0]), 2),
                    "change_pct": 0,
                })
        except Exception:
            continue

    try:
        watchlist = get_supabase().table("watchlist").select("ticker").execute()
        scores = (
            get_supabase().table("scores")
            .select("ticker,technical_score,calculated_at")
            .eq("horizon", "short")
            .order("calculated_at", desc=True)
            .limit(200)
            .execute()
        )

        latest_by_ticker = {}
        for row in scores.data:
            if row["ticker"] not in latest_by_ticker:
                latest_by_ticker[row["ticker"]] = row

        all_scores = sorted(
            latest_by_ticker.values(),
            key=lambda x: x.get("technical_score") or 0,
            reverse=True
        )

        top_gainers = [s for s in all_scores if (s.get("technical_score") or 0) > 0][:5]
        top_losers = [s for s in all_scores if (s.get("technical_score") or 0) < 0][-5:][::-1]
    except Exception:
        top_gainers = []
        top_losers = []

    return {
        "indices": index_data,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "updated_at": datetime.now().isoformat(),
    }


def get_sector_performance() -> list:
    try:
        symbols = json.loads(open(os.path.join(os.path.dirname(__file__), "bist_symbols.json")).read())
        sector_map = {}
        for s in symbols:
            sector = s.get("sector", "Diğer")
            if sector not in sector_map:
                sector_map[sector] = []
            sector_map[sector].append(s["ticker"] + ".IS")

        sector_scores = []
        for sector, tickers in sector_map.items():
            scores_list = []
            for t in tickers[:10]:
                try:
                    res = (
                        get_supabase().table("scores")
                        .select("technical_score")
                        .eq("ticker", t)
                        .eq("horizon", "short")
                        .order("calculated_at", desc=True)
                        .limit(1)
                        .execute()
                    )
                    if res.data and res.data[0].get("technical_score") is not None:
                        scores_list.append(res.data[0]["technical_score"])
                except Exception:
                    continue

            if scores_list:
                avg_score = sum(scores_list) / len(scores_list)
                sector_scores.append({
                    "sector": sector,
                    "avg_score": round(avg_score, 2),
                    "stock_count": len(tickers),
                    "analyzed_count": len(scores_list),
                })

        return sorted(sector_scores, key=lambda x: x["avg_score"], reverse=True)
    except Exception:
        return []
