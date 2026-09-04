from datetime import datetime,timedelta,timezone
from terminal.backtest_engine import optimize,run,walk_forward
from terminal.models import Candle,Freshness
def data(count=700):
 now=datetime(2020,1,1,tzinfo=timezone.utc);out=[]
 for i in range(count):
  price=100+i*.08+8*((i%60)/60);out.append(Candle(instrument_id="x",timeframe="1d",open_time=now+timedelta(days=i),open=price,high=price+2,low=price-2,close=price+(.5 if i%3 else -.4),volume=1000+i%20*100,source="test",freshness=Freshness.delayed))
 return out
def test_all_phase4_strategies_execute_without_lookahead():
 for strategy in ["ma_cross","rsi_reversion","breakout","momentum","vwap_reclaim"]:
  result=run(data(180),strategy,10,30);assert result["assumptions"]["look_ahead_protection"] and "sortino" in result and "underwater_curve" in result
def test_optimization_keeps_out_of_sample_separate():
 result=optimize(data(500));assert result["split"]["out_of_sample"]>0 and all("out_of_sample_return_pct" in x for x in result["results"])
def test_walk_forward_reports_only_oos_windows():
 result=walk_forward(data(),train_bars=252,test_bars=63);assert result["window_count"]>=5 and all("out_of_sample_return_pct" in x for x in result["windows"])
