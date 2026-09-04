import asyncio,json
from abc import ABC,abstractmethod
from datetime import datetime,timezone
from urllib.request import Request,urlopen
import pandas as pd
import yfinance as yf
from .models import Candle,Freshness,Fundamentals,Instrument,Quote
VALID={"1m","3m","5m","15m","30m","1h","4h","1d","1wk","1mo"}
class MarketDataProvider(ABC):
 name:str
 @abstractmethod
 async def quote(self,instrument): ...
 @abstractmethod
 async def candles(self,instrument,timeframe,limit): ...
 async def health(self): return {"provider":self.name,"status":"ok","checked_at":datetime.now(timezone.utc).isoformat()}
 async def fundamentals(self,instrument):raise ValueError("Fundamentals unavailable")
 async def statements(self,instrument,frequency):raise ValueError("Statements unavailable")
 async def actions(self,instrument):return []
class BinanceProvider(MarketDataProvider):
 name="binance"; base="https://api.binance.com/api/v3"
 @staticmethod
 def get(path):
  with urlopen(Request(BinanceProvider.base+path,headers={"User-Agent":"GlobalTerminal/1.0"}),timeout=8) as r:return json.loads(r.read())
 async def quote(self,i):
  d=await asyncio.to_thread(self.get,f"/ticker/24hr?symbol={i.provider_symbols['binance']}")
  return Quote(instrument_id=i.id,price=float(d["lastPrice"]),bid=float(d["bidPrice"]),ask=float(d["askPrice"]),change=float(d["priceChange"]),change_pct=float(d["priceChangePercent"]),volume=float(d["quoteVolume"]),source=self.name,freshness=Freshness.live,as_of=datetime.now(timezone.utc),market_status="open")
 async def candles(self,i,timeframe,limit):
  if timeframe not in VALID: raise ValueError("Unsupported timeframe")
  d=await asyncio.to_thread(self.get,f"/klines?symbol={i.provider_symbols['binance']}&interval={timeframe}&limit={min(limit,1000)}")
  return [Candle(instrument_id=i.id,timeframe=timeframe,open_time=datetime.fromtimestamp(r[0]/1000,tz=timezone.utc),open=float(r[1]),high=float(r[2]),low=float(r[3]),close=float(r[4]),volume=float(r[5]),source=self.name,freshness=Freshness.live) for r in d]
 async def fundamentals(self,i):
  coin=i.provider_symbols.get("coingecko")
  if not coin:raise ValueError("Crypto metadata unavailable")
  def fetch():
   with urlopen(Request(f"https://api.coingecko.com/api/v3/coins/{coin}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false",headers={"User-Agent":"GlobalTerminal/1.0"}),timeout=10) as r:return json.loads(r.read())
  d=await asyncio.to_thread(fetch);m=d.get("market_data",{});quote=(i.quote_currency or "usd").lower()
  return Fundamentals(instrument_id=i.id,source="coingecko",freshness=Freshness.delayed,as_of=datetime.now(timezone.utc),currency=i.quote_currency,market_cap=m.get("market_cap",{}).get(quote),fully_diluted_valuation=m.get("fully_diluted_valuation",{}).get(quote),circulating_supply=m.get("circulating_supply"),total_supply=m.get("total_supply"),fifty_two_week_high=m.get("ath",{}).get(quote),fifty_two_week_low=m.get("atl",{}).get(quote))
class YahooProvider(MarketDataProvider):
 name="yfinance"; intervals={"1m":"1m","5m":"5m","15m":"15m","30m":"30m","1h":"1h","1d":"1d","1wk":"1wk","1mo":"1mo"}
 async def history(self,i,tf):
  if tf not in self.intervals: raise ValueError("Unsupported timeframe for this provider")
  period="7d" if tf=="1m" else "60d" if tf in {"5m","15m","30m","1h"} else "2y"
  return await asyncio.to_thread(yf.Ticker(i.provider_symbols["yfinance"]).history,period=period,interval=self.intervals[tf],auto_adjust=False)
 async def quote(self,i):
  f=await self.history(i,"1d")
  if f.empty: raise ValueError("No market data")
  cur=float(f.Close.iloc[-1]); prev=float(f.Close.iloc[-2]) if len(f)>1 else cur
  return Quote(instrument_id=i.id,price=cur,change=cur-prev,change_pct=(cur/prev-1)*100 if prev else None,volume=float(f.Volume.iloc[-1]),source=self.name,freshness=Freshness.delayed,as_of=f.index[-1].to_pydatetime(),market_status="delayed")
 async def candles(self,i,timeframe,limit):
  f=await self.history(i,timeframe); out=[]
  for stamp,r in f.tail(limit).iterrows():
   if pd.isna(r.Close):continue
   dt=stamp.to_pydatetime(); dt=dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
   out.append(Candle(instrument_id=i.id,timeframe=timeframe,open_time=dt,open=float(r.Open),high=float(r.High),low=float(r.Low),close=float(r.Close),volume=float(r.get("Volume",0) or 0),source=self.name,freshness=Freshness.delayed))
  return out
 async def fundamentals(self,i):
  info=await asyncio.to_thread(lambda:yf.Ticker(i.provider_symbols["yfinance"]).info)
  def num(key):
   value=info.get(key)
   try:return float(value) if value is not None and pd.notna(value) else None
   except (TypeError,ValueError):return None
  docs=[]
  if i.country=="US":docs.append({"label":"SEC EDGAR","url":f"https://www.sec.gov/edgar/search/#/q={i.symbol}"})
  if i.mic=="XIST":docs.append({"label":"KAP Bildirimleri","url":f"https://www.kap.org.tr/tr/sirket-bilgileri/ozet/{i.symbol}"})
  return Fundamentals(instrument_id=i.id,source=self.name,freshness=Freshness.delayed,as_of=datetime.now(timezone.utc),currency=i.currency,market_cap=num("marketCap"),enterprise_value=num("enterpriseValue"),trailing_pe=num("trailingPE"),forward_pe=num("forwardPE"),price_to_book=num("priceToBook"),enterprise_to_ebitda=num("enterpriseToEbitda"),dividend_yield=num("dividendYield"),revenue_growth=num("revenueGrowth"),profit_margin=num("profitMargins"),return_on_equity=num("returnOnEquity"),total_revenue=num("totalRevenue"),free_cash_flow=num("freeCashflow"),total_debt=num("totalDebt"),total_cash=num("totalCash"),fifty_two_week_high=num("fiftyTwoWeekHigh"),fifty_two_week_low=num("fiftyTwoWeekLow"),sector=info.get("sector"),industry=info.get("industry"),documents=docs)
 async def statements(self,i,frequency):
  from .models import StatementPeriod
  ticker=yf.Ticker(i.provider_symbols["yfinance"])
  def fetch():return (ticker.quarterly_income_stmt,ticker.quarterly_balance_sheet,ticker.quarterly_cashflow) if frequency=="quarterly" else (ticker.income_stmt,ticker.balance_sheet,ticker.cashflow)
  income,balance,cash=await asyncio.to_thread(fetch);columns=list(dict.fromkeys([*income.columns,*balance.columns,*cash.columns]))[:8]
  aliases={"income":{"revenue":["Total Revenue"],"gross_profit":["Gross Profit"],"operating_income":["Operating Income"],"ebitda":["EBITDA","Normalized EBITDA"],"net_income":["Net Income","Net Income Common Stockholders"]},"balance":{"cash":["Cash Cash Equivalents And Short Term Investments","Cash And Cash Equivalents"],"total_assets":["Total Assets"],"total_debt":["Total Debt"],"equity":["Stockholders Equity","Total Equity Gross Minority Interest"]},"cashflow":{"operating_cash_flow":["Operating Cash Flow"],"capital_expenditure":["Capital Expenditure"],"free_cash_flow":["Free Cash Flow"]}}
  def values(frame,mapping,col):
   out={}
   for key,names in mapping.items():
    value=next((frame.at[name,col] for name in names if name in frame.index and col in frame.columns),None)
    try:out[key]=float(value) if value is not None and pd.notna(value) else None
    except (TypeError,ValueError):out[key]=None
   return out
  return [StatementPeriod(period=col.strftime("%Y-%m-%d"),frequency=frequency,currency=i.currency,income=values(income,aliases["income"],col),balance=values(balance,aliases["balance"],col),cashflow=values(cash,aliases["cashflow"],col),source=self.name,as_of=datetime.now(timezone.utc)) for col in columns]
 async def actions(self,i):
  from .models import CorporateAction
  frame=await asyncio.to_thread(lambda:yf.Ticker(i.provider_symbols["yfinance"]).actions);out=[]
  for stamp,row in frame.tail(30).iterrows():
   dt=stamp.to_pydatetime();dt=dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
   if float(row.get("Dividends",0) or 0)>0:out.append(CorporateAction(instrument_id=i.id,action_type="dividend",event_date=dt,value=float(row["Dividends"]),currency=i.currency,title="Nakit temettü",source=self.name))
   if float(row.get("Stock Splits",0) or 0)>0:out.append(CorporateAction(instrument_id=i.id,action_type="split",event_date=dt,value=float(row["Stock Splits"]),title="Hisse bölünmesi",source=self.name))
  return sorted(out,key=lambda x:x.event_date,reverse=True)
class ProviderRouter:
 def __init__(self):self.providers={"binance":BinanceProvider(),"yfinance":YahooProvider()}
 def for_instrument(self,i):
  for n in ("binance","yfinance"):
   if n in i.provider_symbols:return self.providers[n]
  raise ValueError("No provider")
providers=ProviderRouter()
