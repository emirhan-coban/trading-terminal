from .catalog import catalog
from .models import Quote
def screen(quotes:list[Quote],asset_class=None,exchange=None,min_price=None,max_price=None,min_change_pct=None,max_change_pct=None,sort="change_pct",direction="desc"):
 rows=[]
 for q in quotes:
  i=catalog.get(q.instrument_id)
  if not i or asset_class and i.asset_class.value!=asset_class or exchange and i.exchange!=exchange:continue
  if min_price is not None and (q.price is None or q.price<min_price):continue
  if max_price is not None and (q.price is None or q.price>max_price):continue
  if min_change_pct is not None and (q.change_pct is None or q.change_pct<min_change_pct):continue
  if max_change_pct is not None and (q.change_pct is None or q.change_pct>max_change_pct):continue
  rows.append({"instrument":i.model_dump(),"quote":q.model_dump()})
 rows.sort(key=lambda x:(x["quote"].get(sort) is not None,x["quote"].get(sort) or 0),reverse=direction=="desc")
 return rows
