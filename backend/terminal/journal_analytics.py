from collections import defaultdict
def summarize_orders(orders):
 def val(x,key,default=0):return x.get(key,default) if isinstance(x,dict) else getattr(x,key,default)
 filled=[x for x in orders if val(x,"status")=="filled"];sells=[x for x in filled if val(x,"side")=="sell"];pnls=[float(val(x,"realized_pnl") or 0) for x in sells];wins=[x for x in pnls if x>0];losses=[x for x in pnls if x<=0];by=defaultdict(lambda:{"trades":0,"realized_pnl":0.})
 for x in sells:row=by[val(x,"instrument_id")];row["trades"]+=1;row["realized_pnl"]+=float(val(x,"realized_pnl") or 0)
 profit=sum(wins);loss=abs(sum(losses));return {"filled_orders":len(filled),"closed_trades":len(sells),"win_rate_pct":round(len(wins)/len(pnls)*100,2) if pnls else None,"realized_pnl":round(sum(pnls),2),"expectancy":round(sum(pnls)/len(pnls),2) if pnls else 0,"profit_factor":round(profit/loss,2) if loss else None,"commissions":round(sum(float(val(x,"commission") or 0) for x in filled),2),"by_instrument":dict(by)}
