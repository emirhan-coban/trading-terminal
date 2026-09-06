from __future__ import annotations
import asyncio,json
from dataclasses import dataclass
from .providers import BinanceProvider

def normalize_binance(message:dict,instrument_id:str)->dict|None:
 data=message.get("data",message);event=data.get("e")
 if event=="trade":return {"type":"trade","instrument_id":instrument_id,"event_time":data["E"],"trade_id":data["t"],"price":float(data["p"]),"quantity":float(data["q"]),"buyer_maker":bool(data["m"])}
 if event=="kline":
  k=data["k"];return {"type":"candle","instrument_id":instrument_id,"event_time":data["E"],"timeframe":k["i"],"open_time":k["t"],"close_time":k["T"],"open":float(k["o"]),"high":float(k["h"]),"low":float(k["l"]),"close":float(k["c"]),"volume":float(k["v"]),"closed":bool(k["x"])}
 if event=="depthUpdate":return {"type":"depth","instrument_id":instrument_id,"event_time":data["E"],"first_update_id":data["U"],"final_update_id":data["u"],"bids":[[float(p),float(q)] for p,q in data["b"]],"asks":[[float(p),float(q)] for p,q in data["a"]]}
 return None

@dataclass
class DepthBook:
 last_update_id:int=0;bids:dict=None;asks:dict=None
 def __post_init__(self):self.bids={} if self.bids is None else self.bids;self.asks={} if self.asks is None else self.asks
 def snapshot(self,data):self.last_update_id=int(data["lastUpdateId"]);self.bids={float(p):float(q) for p,q in data["bids"]};self.asks={float(p):float(q) for p,q in data["asks"]}
 def apply(self,event):
  if event["final_update_id"]<=self.last_update_id:return "stale"
  if self.last_update_id and event["first_update_id"]>self.last_update_id+1:return "gap"
  for side,key in ((self.bids,"bids"),(self.asks,"asks")):
   for price,qty in event[key]:
    if qty==0:side.pop(price,None)
    else:side[price]=qty
  self.last_update_id=event["final_update_id"];return "applied"
 def top(self,limit=20):return {"last_update_id":self.last_update_id,"bids":sorted(self.bids.items(),reverse=True)[:limit],"asks":sorted(self.asks.items())[:limit]}

async def binance_events(instrument,interval="1m"):
 import websockets
 symbol=instrument.provider_symbols["binance"].lower();streams=f"{symbol}@trade/{symbol}@kline_{interval}/{symbol}@depth@100ms";urls=(f"wss://stream.binance.vision/stream?streams={streams}",f"wss://stream.binance.com:9443/stream?streams={streams}");backoff=1;endpoint=0
 while True:
  try:
   async with websockets.connect(urls[endpoint],ping_interval=20,ping_timeout=20,close_timeout=5) as ws:
    backoff=1
    async for raw in ws:
     event=normalize_binance(json.loads(raw),instrument.id)
     if event:yield event
  except asyncio.CancelledError:raise
  except Exception:
   endpoint=(endpoint+1)%len(urls)
   await asyncio.sleep(backoff);backoff=min(backoff*2,30)

async def depth_snapshot(instrument):
 symbol=instrument.provider_symbols["binance"];return await asyncio.to_thread(BinanceProvider.get,f"/depth?symbol={symbol}&limit=100")
