"""Source-backed company event calendar; never invents missing dates."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf


async def events_for(instrument):
    symbol = instrument.provider_symbols.get("yfinance")
    if not symbol:
        return []

    def fetch():
        return yf.Ticker(symbol).calendar

    raw = await asyncio.to_thread(fetch)
    if raw is None:
        return []
    data = raw.to_dict() if hasattr(raw, "to_dict") else dict(raw)
    events = []
    aliases = {
        "Earnings Date": "earnings",
        "Ex-Dividend Date": "ex_dividend",
        "Dividend Date": "dividend_payment",
    }
    for key, event_type in aliases.items():
        value = data.get(key)
        values = value if isinstance(value, (list, tuple)) else [value]
        for item in values:
            if item is None or (not isinstance(item, (datetime, pd.Timestamp)) and pd.isna(item)):
                continue
            stamp = item.to_pydatetime() if isinstance(item, pd.Timestamp) else item
            stamp = stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)
            events.append({"instrument_id": instrument.id, "event_type": event_type, "title": key,
                           "starts_at": stamp, "source": "yfinance", "freshness": "delayed"})
    return sorted(events, key=lambda row: row["starts_at"])
