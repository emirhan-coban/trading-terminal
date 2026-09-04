from __future__ import annotations
import math
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .models import Candle

@dataclass
class Costs:
 commission_rate:float=.001
 slippage_rate:float=.0005

def _signals(frame:pd.DataFrame,strategy:str,fast:int,slow:int)->pd.Series:
 if strategy=="ma_cross":
  if fast>=slow:raise ValueError("fast must be smaller than slow")
  a=frame.close.rolling(fast).mean();b=frame.close.rolling(slow).mean();state=(a>b).astype(int)
 elif strategy=="rsi_reversion":
  delta=frame.close.diff();gain=delta.clip(lower=0).rolling(14).mean();loss=(-delta.clip(upper=0)).rolling(14).mean();rsi=100-(100/(1+gain/loss));state=pd.Series(0,index=frame.index);state[rsi<30]=1;state[rsi>70]=-1;state=state.ffill().fillna(0)
 elif strategy=="breakout":
  high=frame.high.shift(1).rolling(slow).max();low=frame.low.shift(1).rolling(fast).min();state=pd.Series(0,index=frame.index);state[frame.close>high]=1;state[frame.close<low]=-1;state=state.replace(0,np.nan).ffill().fillna(0)
 elif strategy=="momentum":
  momentum=frame.close/frame.close.shift(slow)-1;state=(momentum>0).astype(int)
 elif strategy=="vwap_reclaim":
  typical=(frame.high+frame.low+frame.close)/3;vwap=(typical*frame.volume).rolling(slow).sum()/frame.volume.rolling(slow).sum();state=(frame.close>vwap).astype(int)
 else:raise ValueError("unknown strategy")
 # Signal from bar N is executable only at bar N+1 open.
 return state.diff().fillna(0).shift(1).fillna(0)

def run(candles:list[Candle],strategy="ma_cross",fast=20,slow=50,capital=100000,costs=Costs()):
 if len(candles)<max(60,slow+2):raise ValueError("not enough candles")
 frame=pd.DataFrame([{"time":x.open_time,"open":x.open,"high":x.high,"low":x.low,"close":x.close,"volume":x.volume} for x in candles]);frame["signal"]=_signals(frame,strategy,fast,slow)
 cash=float(capital);shares=0.;entry_cost=0.;trades=[];equity=[];returns=[]
 for row in frame.itertuples():
  if row.signal>0 and shares==0:
   price=row.open*(1+costs.slippage_rate);shares=cash/(price*(1+costs.commission_rate));fee=shares*price*costs.commission_rate;entry_cost=cash;cash=0;trades.append({"time":row.time.isoformat(),"side":"buy","price":price,"quantity":shares,"commission":fee})
  elif row.signal<0 and shares>0:
   price=row.open*(1-costs.slippage_rate);gross=shares*price;fee=gross*costs.commission_rate;cash=gross-fee;trades.append({"time":row.time.isoformat(),"side":"sell","price":price,"quantity":shares,"commission":fee,"pnl":cash-entry_cost});shares=0
  value=cash+shares*row.close
  if equity:returns.append(value/equity[-1]["value"]-1)
  equity.append({"time":row.time.isoformat(),"value":value})
 final=equity[-1]["value"];peak=0.;max_dd=0.
 for x in equity:peak=max(peak,x["value"]);max_dd=min(max_dd,x["value"]/peak-1 if peak else 0)
 mean=sum(returns)/len(returns) if returns else 0;variance=sum((x-mean)**2 for x in returns)/(len(returns)-1) if len(returns)>1 else 0;sharpe=mean/math.sqrt(variance)*math.sqrt(252) if variance>0 else 0;downside=[x for x in returns if x<0];down_var=sum(x*x for x in downside)/len(downside) if downside else 0;sortino=mean/math.sqrt(down_var)*math.sqrt(252) if down_var else 0;years=max(len(frame)/252,1/252);cagr=(final/capital)**(1/years)-1;calmar=cagr/abs(max_dd) if max_dd else None
 sells=[x for x in trades if x["side"]=="sell"];wins=[x for x in sells if x.get("pnl",0)>0];losses=[x for x in sells if x.get("pnl",0)<=0];profits=sum(x["pnl"] for x in wins);loss_total=abs(sum(x["pnl"] for x in losses))
 closed_pnl=[x.get("pnl",0) for x in sells];expectancy=sum(closed_pnl)/len(closed_pnl) if closed_pnl else 0;turnover=sum(x["price"]*x["quantity"] for x in trades)/capital
 underwater=[{"time":x["time"],"drawdown_pct":round((x["value"]/max(y["value"] for y in equity[:n+1])-1)*100,3)} for n,x in enumerate(equity)]
 return {"strategy":strategy,"parameters":{"fast":fast,"slow":slow},"initial_capital":capital,"final_value":round(final,2),"return_pct":round((final/capital-1)*100,2),"cagr_pct":round(cagr*100,2),"max_drawdown_pct":round(max_dd*100,2),"sharpe":round(sharpe,2),"sortino":round(sortino,2),"calmar":round(calmar,2) if calmar is not None else None,"profit_factor":round(profits/loss_total,2) if loss_total else None,"expectancy":round(expectancy,2),"turnover":round(turnover,2),"win_rate_pct":round(len(wins)/len(sells)*100,2) if sells else None,"trades":trades,"equity_curve":equity[::max(1,len(equity)//200)],"underwater_curve":underwater[::max(1,len(underwater)//200)],"assumptions":{"commission_rate":costs.commission_rate,"slippage_rate":costs.slippage_rate,"execution":"next_bar_open","dividends_included":False,"look_ahead_protection":True}}

def walk_forward(candles:list[Candle],strategy="ma_cross",train_bars=252,test_bars=63,parameter_grid=None):
 grid=parameter_grid or [(10,30),(20,50),(30,100)];windows=[];cursor=0
 while cursor+train_bars+test_bars<=len(candles):
  train=candles[cursor:cursor+train_bars];test=candles[cursor+train_bars:cursor+train_bars+test_bars];candidates=[]
  for fast,slow in grid:
   if slow+2>test_bars:continue
   try:candidates.append((run(train,strategy,fast,slow)["sharpe"],fast,slow))
   except ValueError:continue
  if not candidates:break
  _,fast,slow=max(candidates);result=run(test,strategy,fast,slow);windows.append({"train_start":train[0].open_time,"test_start":test[0].open_time,"test_end":test[-1].open_time,"selected":{"fast":fast,"slow":slow},"out_of_sample_return_pct":result["return_pct"],"out_of_sample_sharpe":result["sharpe"]});cursor+=test_bars
 returns=[x["out_of_sample_return_pct"] for x in windows];positive=sum(x>0 for x in returns)
 return {"strategy":strategy,"windows":windows,"window_count":len(windows),"positive_window_pct":round(positive/len(windows)*100,2) if windows else None,"aggregate_oos_return_pct":round(sum(returns),2),"warning":"Parameter selection is exploratory; validate on unseen data."}

def optimize(candles:list[Candle],strategy="ma_cross",grid=None,split=.7):
 cut=max(60,int(len(candles)*split));train,test=candles[:cut],candles[cut:];grid=grid or [(5,20),(10,30),(20,50),(30,100)];rows=[]
 for fast,slow in grid:
  try:
   inside=run(train,strategy,fast,slow);outside=run(test,strategy,fast,slow);decay=inside["sharpe"]-outside["sharpe"];rows.append({"fast":fast,"slow":slow,"in_sample_return_pct":inside["return_pct"],"out_of_sample_return_pct":outside["return_pct"],"in_sample_sharpe":inside["sharpe"],"out_of_sample_sharpe":outside["sharpe"],"sharpe_decay":round(decay,2)})
  except ValueError:continue
 rows.sort(key=lambda x:x["in_sample_sharpe"],reverse=True);best=rows[0] if rows else None;warnings=[]
 if best and (best["out_of_sample_return_pct"]<0 or best["sharpe_decay"]>1):warnings.append("OVERFITTING_RISK")
 return {"strategy":strategy,"split":{"in_sample":split,"out_of_sample":1-split},"results":rows,"selected":best,"warnings":warnings}
