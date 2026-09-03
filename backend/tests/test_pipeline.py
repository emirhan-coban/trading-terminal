"""Saf fonksiyon testleri — ağ / Supabase gerektirmez."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline import normalize_ticker, _db_horizon, _num, compute_score, clean_nan


def test_normalize_ticker():
    assert normalize_ticker("thyao") == "THYAO.IS"
    assert normalize_ticker("THYAO") == "THYAO.IS"
    assert normalize_ticker("THYAO.IS") == "THYAO.IS"
    assert normalize_ticker("  garan.is ") == "GARAN.IS"


def test_db_horizon_mapping():
    assert _db_horizon("1d") == "short"
    assert _db_horizon("1w") == "medium"
    assert _db_horizon("1M") == "long"
    assert _db_horizon("bilinmeyen") == "short"


def test_num_sanitizer():
    assert _num(4.28) == 4.28
    assert _num(None) is None
    assert _num(float("nan")) is None
    assert _num(float("inf")) is None
    assert _num("bozuk") is None


def test_clean_nan():
    assert clean_nan(float("nan")) is None
    assert clean_nan({"a": float("inf"), "b": [1, float("nan")]}) == {"a": None, "b": [1, None]}
    assert clean_nan(5) == 5


def test_compute_score_bullish():
    ind = {"rsi": 70, "macd_hist": 1.5, "sma20": 100, "sma50": 90,
           "close": 110, "adx": 30, "cci": 150, "williams_r": -90}
    score = compute_score(ind)
    assert score > 50


def test_compute_score_bearish():
    ind = {"rsi": 25, "macd_hist": -1.5, "sma20": 100, "sma50": 90,
           "close": 80, "adx": 30, "cci": -150, "williams_r": -10}
    score = compute_score(ind)
    assert score < -50


def test_compute_score_neutral_and_empty():
    assert compute_score({"rsi": 50, "macd_hist": None}) == 0
    assert compute_score({}) == 0


def test_compute_score_clamped():
    ind = {"rsi": 100, "macd_hist": 99, "sma20": 1, "sma50": 1,
           "close": 10**9, "adx": 99, "cci": 10**6, "williams_r": -99}
    assert compute_score(ind) == 100
    bearish = {"rsi": 0, "macd_hist": -99, "sma20": 10**9, "sma50": 10**9,
               "close": 1, "adx": 99, "cci": -10**6, "williams_r": -10}
    assert compute_score(bearish) == -100
    assert math.isfinite(compute_score(bearish))
