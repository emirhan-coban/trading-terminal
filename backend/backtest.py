"""Basit strateji backtest'i — DB'deki price_history üzerinden, ağ yok.

Stratejiler (long-only, başlangıç 100.000 ₺ varsayılan):
  ma_cross : SMA(fast) SMA(slow)'yu yukarı kesince al, aşağı kesince sat
  rsi      : RSI rsi_buy altına inince al, rsi_sell üstüne çıkınca sat
"""

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator

from pipeline import get_supabase, normalize_ticker


def _load_prices(ticker: str) -> pd.DataFrame:
    res = (
        get_supabase().table("price_history")
        .select("date,close")
        .eq("ticker", ticker)
        .order("date")
        .execute()
    )
    df = pd.DataFrame(res.data or [])
    if len(df) < 60:
        raise ValueError(f"{ticker} için backtest'e yetecek veri yok ({len(df)} satır, en az 60 gerekli).")
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["close"]).reset_index(drop=True)
    return df


def _simulate(df: pd.DataFrame, capital: float = 100_000.0) -> dict:
    cash, shares = capital, 0.0
    trades = []
    equity = []

    for _, row in df.iterrows():
        price = float(row["close"])
        if row["signal"] == 1 and shares == 0 and cash > 0:
            shares = cash / price
            cash = 0.0
            trades.append({"date": str(row["date"].date()), "side": "BUY", "price": round(price, 2)})
        elif row["signal"] == -1 and shares > 0:
            cash = shares * price
            shares = 0.0
            trades.append({"date": str(row["date"].date()), "side": "SELL", "price": round(price, 2)})
        equity.append({"date": str(row["date"].date()),
                       "value": round(cash + shares * price, 2)})

    final = cash + shares * float(df.iloc[-1]["close"])
    start_price, end_price = float(df.iloc[0]["close"]), float(df.iloc[-1]["close"])
    buy_hold = capital * (end_price / start_price)

    # Örnekleme: equity eğrisini ~120 noktaya indir (tavan bölme)
    step = max(1, -(-len(equity) // 120))
    equity_sampled = equity[::step]
    if equity_sampled[-1] != equity[-1]:
        equity_sampled.append(equity[-1])

    sells = [t for t in trades if t["side"] == "SELL"]
    return {
        "final_value": round(final, 2),
        "strategy_return_pct": round((final - capital) / capital * 100, 2),
        "buy_hold_return_pct": round((buy_hold - capital) / capital * 100, 2),
        "trades_count": len(trades),
        "sell_count": len(sells),
        "in_position": shares > 0,
        "equity_curve": equity_sampled,
        "recent_trades": trades[-20:],
    }


def run_backtest(ticker_raw: str, strategy: str = "ma_cross",
                 fast: int = 20, slow: int = 50,
                 rsi_buy: float = 30.0, rsi_sell: float = 70.0,
                 capital: float = 100_000.0) -> dict:
    ticker = normalize_ticker(ticker_raw)
    df = _load_prices(ticker)

    if strategy == "ma_cross":
        if fast >= slow:
            raise ValueError("fast, slow'dan küçük olmalı.")
        df["fast_ma"] = SMAIndicator(close=df["close"], window=fast).sma_indicator()
        df["slow_ma"] = SMAIndicator(close=df["close"], window=slow).sma_indicator()
        df = df.dropna().reset_index(drop=True)
        df["signal"] = 0
        df.loc[df["fast_ma"] > df["slow_ma"], "signal"] = 1
        df.loc[df["fast_ma"] <= df["slow_ma"], "signal"] = -1
        # Sadece kesişim günlerinde işlem yap (sinyal değişimi)
        df["signal"] = df["signal"].where(df["signal"] != df["signal"].shift(1), 0)
        params = {"fast": fast, "slow": slow}
    elif strategy == "rsi":
        df["rsi"] = RSIIndicator(close=df["close"], window=14).rsi()
        df = df.dropna().reset_index(drop=True)
        df["signal"] = 0
        df.loc[df["rsi"] < rsi_buy, "signal"] = 1
        df.loc[df["rsi"] > rsi_sell, "signal"] = -1
        df["signal"] = df["signal"].where(df["signal"] != df["signal"].shift(1), 0)
        params = {"rsi_buy": rsi_buy, "rsi_sell": rsi_sell}
    else:
        raise ValueError(f"Bilinmeyen strateji: {strategy} (ma_cross | rsi)")

    result = _simulate(df, capital=capital)
    return {
        "ticker": ticker,
        "strategy": strategy,
        "params": params,
        "capital": capital,
        "period": {"start": str(df.iloc[0]["date"].date()),
                   "end": str(df.iloc[-1]["date"].date()),
                   "bars": len(df)},
        **result,
        "note": "Geçmiş performans geleceği göstermez; komisyon/makas dahil değildir.",
    }
