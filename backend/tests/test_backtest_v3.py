from datetime import datetime,timedelta,timezone
from terminal.backtest_engine import run
from terminal.models import Candle,Freshness
def series():
 start=datetime(2024,1,1,tzinfo=timezone.utc);prices=list(range(100,140))+list(range(140,100,-1))+list(range(100,140))
 return [Candle(instrument_id="x",timeframe="1d",open_time=start+timedelta(days=n),open=p,high=p+1,low=p-1,close=p,volume=1000,source="test",freshness=Freshness.delayed) for n,p in enumerate(prices)]
def test_backtest_uses_next_bar_and_costs():
 candles=series();result=run(candles,fast=3,slow=8)
 first=result["trades"][0];signal_prices=[x.close for x in candles]
 assert first["price"]>signal_prices[7]
 assert first["commission"]>0
 assert result["assumptions"]["execution"]=="next_bar_open"
