from collections import defaultdict
from uuid import uuid4
from .catalog import catalog
from .models import PortfolioTransactionIn
class PortfolioEngine:
 def __init__(self):self.transactions=defaultdict(list);self.snapshots=defaultdict(list)
 def add(self,user,body:PortfolioTransactionIn):
  row={"id":str(uuid4()),"user_id":user,**body.model_dump(mode="json")};self.transactions[user].append(row);return row
 def holdings(self,user):
  state={}
  for tx in sorted(self.transactions[user],key=lambda x:x["executed_at"]):
   if tx["side"] not in {"buy","sell"}:continue
   qty,avg=state.get(tx["instrument_id"],(0.,0.));amount=float(tx["quantity"]);price=float(tx["price"]);fees=float(tx["fees"])
   if tx["side"]=="buy":new=qty+amount;avg=(qty*avg+amount*price+fees)/new;qty=new
   else:qty=max(0,qty-amount)
   if qty:state[tx["instrument_id"]]=(qty,avg)
   else:state.pop(tx["instrument_id"],None)
  return state
 def summary(self,user,quotes,fx,base="USD"):
  positions=[];total=0.;unpriced=[]
  for iid,(qty,avg) in self.holdings(user).items():
   i=catalog.get(iid);q=quotes.get(iid);currency=i.quote_currency or i.currency;rate=fx.get(currency)
   value=q.price*qty if q and q.price is not None else None;base_value=value*rate if value is not None and rate is not None else None
   if base_value is None:unpriced.append(iid)
   else:total+=base_value
   positions.append({"instrument_id":iid,"asset_class":i.asset_class.value,"quantity":qty,"average_price":avg,"last_price":q.price if q else None,"market_value":value,"base_value":base_value,"currency":currency,"fx_rate":rate,"freshness":q.freshness if q else "unavailable"})
  return {"base_currency":base,"total_value":round(total,2),"positions":positions,"unpriced_instruments":unpriced,"complete":not unpriced}
 def snapshot(self,user,summary):
  from datetime import datetime,timezone
  row={"user_id":user,"base_currency":summary["base_currency"],"total_value":summary["total_value"],"external_flow":0.,"as_of":datetime.now(timezone.utc)};self.snapshots[user].append(row);return row
portfolio_engine=PortfolioEngine()
