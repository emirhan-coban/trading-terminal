from __future__ import annotations
from datetime import datetime


def xirr(cashflows:list[tuple[datetime,float]]):
    if len(cashflows)<2 or not any(v<0 for _,v in cashflows) or not any(v>0 for _,v in cashflows):return None
    start=min(d for d,_ in cashflows)
    def value(rate):return sum(v/(1+rate)**((d-start).days/365.25) for d,v in cashflows)
    lo,hi=-.9999,10.
    if value(lo)*value(hi)>0:return None
    for _ in range(100):
        mid=(lo+hi)/2
        if value(lo)*value(mid)<=0:hi=mid
        else:lo=mid
    return round((lo+hi)/2*100,2)


def performance(transactions,current_value):
    flows=[]
    for row in transactions:
        if row["side"] in {"buy","deposit"}:amount=-(float(row["quantity"])*float(row["price"])+float(row.get("fees",0)))
        elif row["side"] in {"sell","dividend","withdrawal"}:amount=float(row["quantity"])*float(row["price"])-float(row.get("fees",0))
        else:continue
        stamp=row["executed_at"];stamp=datetime.fromisoformat(stamp.replace("Z","+00:00")) if isinstance(stamp,str) else stamp;flows.append((stamp,amount))
    if flows:flows.append((datetime.now(flows[0][0].tzinfo),float(current_value)))
    return {"money_weighted_return_pct":xirr(flows),"time_weighted_return_pct":None,"twr_status":"requires_position_snapshots"}

def time_weighted_return(snapshots):
    ordered=sorted(snapshots,key=lambda row:row["as_of"]);factors=[]
    for previous,current in zip(ordered,ordered[1:]):
        start=float(previous["total_value"]);flow=float(current.get("external_flow",0));capital=start+flow
        if capital>0:factors.append(float(current["total_value"])/capital)
    if not factors:return None
    product=1.
    for factor in factors:product*=factor
    return round((product-1)*100,4)


def stress(positions,shocks):
    rows=[];total=0.
    for row in positions:
        value=row.get("base_value")
        if value is None:continue
        shock=float(shocks.get(row.get("asset_class"),shocks.get("default",0)));impact=value*shock;total+=impact;rows.append({"instrument_id":row["instrument_id"],"shock_pct":shock*100,"impact":round(impact,2)})
    return {"total_impact":round(total,2),"positions":rows,"assumptions":shocks}
