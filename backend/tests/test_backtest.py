"""Backtest simülasyonu + alarm değerlendirme testleri (saf fonksiyonlar)."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from backtest import _simulate
from portfolio import _evaluate


def _df(prices, signals):
    dates = pd.date_range("2024-01-01", periods=len(prices), freq="D")
    return pd.DataFrame({"date": dates, "close": prices, "signal": signals})


def test_simulate_profit():
    # Al 100'den, sat 110'dan
    df = _df([100, 102, 100, 105, 110, 108], [0, 0, 1, 0, -1, 0])
    out = _simulate(df, capital=100_000.0)
    assert out["final_value"] == 110_000.0
    assert out["strategy_return_pct"] == 10.0
    assert out["trades_count"] == 2
    assert out["in_position"] is False


def test_simulate_hold_to_end():
    df = _df([100, 110, 120], [1, 0, 0])
    out = _simulate(df, capital=10_000.0)
    assert out["final_value"] == 12_000.0
    assert out["in_position"] is True


def test_simulate_no_trades_matches_buy_hold():
    df = _df([100, 110, 90], [0, 0, 0])
    out = _simulate(df, capital=10_000.0)
    assert out["final_value"] == 10_000.0
    assert out["buy_hold_return_pct"] == -10.0


def test_simulate_equity_curve_sampled():
    df = _df(list(range(1, 300)), [0] * 299)
    out = _simulate(df)
    assert len(out["equity_curve"]) <= 121
    assert out["equity_curve"][-1]["value"] == out["final_value"]


def test_evaluate_conditions():
    sig = {"close": 105.0, "rsi": 72.0, "score": -10.0}
    assert _evaluate("price_above", 100, sig) == (True, 105.0)
    assert _evaluate("price_below", 100, sig) == (False, 105.0)
    assert _evaluate("rsi_above", 70, sig) == (True, 72.0)
    assert _evaluate("rsi_below", 30, sig) == (False, 72.0)
    assert _evaluate("score_below", 0, sig) == (True, -10.0)
    assert _evaluate("score_above", 0, sig) == (False, -10.0)


def test_evaluate_missing_data_no_trigger():
    assert _evaluate("price_above", 100, {"close": None}) == (False, None)
    assert _evaluate("rsi_below", 30, {}) == (False, None)
