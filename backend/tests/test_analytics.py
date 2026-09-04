from datetime import datetime,timedelta,timezone
from terminal.analytics import portfolio_risk,technical_snapshot
from terminal.models import Candle,Freshness
def candles(start=100,count=80):
 now=datetime(2025,1,1,tzinfo=timezone.utc);return [Candle(instrument_id="x",timeframe="1d",open_time=now+timedelta(days=i),open=start+i,high=start+i+2,low=start+i-1,close=start+i+1,volume=1000+i*10,source="test",freshness=Freshness.delayed) for i in range(count)]
def test_technical_snapshot_is_explainable():
 x=technical_snapshot(candles());assert set(["rsi","atr_pct","volatility","relative_volume","momentum_20d","trend_score"]).issubset(x);assert x["trend_score"]==100
def test_portfolio_risk_returns_risk_metrics():
 x=portfolio_risk({"a":[100+i for i in range(80)],"b":[200+i*.5 for i in range(80)]},{"a":.6,"b":.4},[300+i for i in range(80)]);assert x["complete"] and x["observations"]>20 and "correlation" in x
def test_insufficient_risk_history_is_explicit():assert portfolio_risk({"a":[1,2]},{"a":1})["reason"]=="insufficient_history"
