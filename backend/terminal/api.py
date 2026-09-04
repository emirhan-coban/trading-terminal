import asyncio,json
from datetime import datetime,timezone
from fastapi import APIRouter,Header,HTTPException,Query,WebSocket,WebSocketDisconnect,Response
from .catalog import catalog
from .models import AlertIn,ApiMeta,ApiResponse,Freshness,JournalEntryIn,PaperOrderIn,PortfolioTransactionIn,Quote,SavedScreenIn,WorkspaceIn
from .paper import paper_broker
from .providers import providers
from .alerts import alerts
from .journal import journal
from .screener import screen
from .backtest_engine import optimize as optimize_backtest,run as run_backtest,walk_forward
from .auth import authenticate
from .cache import quote_cache
from .persistence import repository
from .research import news_for
from .portfolio_v3 import portfolio_engine
from .analytics import portfolio_risk,technical_snapshot
from .screens import screens
from .ai_research import summarize
from .journal_analytics import summarize_orders
from .market_stream import DepthBook,binance_events,depth_snapshot
from .brokers import live_broker
from .workspaces import workspaces
from .calendar import events_for
from .portfolio_performance import performance,stress,time_weighted_return
from .filings import sec_filings
router=APIRouter(prefix="/api/v1")
def cursor_page(rows,cursor,limit):
 start=0
 if cursor:
  start=next((n+1 for n,row in enumerate(rows) if str(row.get("id") if isinstance(row,dict) else row.id)==cursor),0)
 page=rows[start:start+limit];next_cursor=None
 if start+limit<len(rows) and page:next_cursor=str(page[-1].get("id") if isinstance(page[-1],dict) else page[-1].id)
 return page,next_cursor
async def uid(auth):return (await authenticate(auth)).user_id
async def get_quote(iid):
 i=catalog.get(iid)
 if not i:raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 try:
  quote=await providers.for_instrument(i).quote(i);await quote_cache.set(iid,quote.model_dump(mode="json"),90);return quote
 except Exception as e:
  cached=await quote_cache.get(iid)
  if cached:
   cached["freshness"]="stale";cached["source"]=f"{cached.get('source','cache')}+cache";return Quote.model_validate(cached)
  raise HTTPException(503,detail={"code":"PROVIDER_UNAVAILABLE","message":"Piyasa verisi alınamıyor","retryable":True}) from e
async def hydrate_paper(user):
 if not repository.enabled or paper_broker.holdings[user] or paper_broker.orders[user]:return
 stored=await repository.list("paper_positions",user,"updated_at") or []
 paper_broker.holdings[user]={x["instrument_id"]:(float(x["quantity"]),float(x["average_price"])) for x in stored}
 accounts=await repository.list("paper_accounts",user,"created_at") or []
 if accounts:paper_broker.cash[user]=float(accounts[0]["cash_balance"])
async def persist_paper_events(user,orders):
 for row in orders:await repository.upsert("paper_orders",row.model_dump(mode="json"))
 for fill in paper_broker.fills[user]:await repository.upsert("paper_fills",fill)
 for cash_event in paper_broker.cash_ledger[user]:await repository.upsert("cash_ledger",cash_event)
 for event in paper_broker.audit[user]:await repository.upsert("audit_events",event)
@router.get("/instruments/search",response_model=ApiResponse)
async def search(q:str=Query(min_length=1),asset_class:str|None=None,limit:int=Query(20,ge=1,le=50)):return ApiResponse(data=[x.model_dump() for x in catalog.search(q,asset_class,limit)],meta=ApiMeta(source="instrument-catalog",freshness=Freshness.live))
@router.get("/instruments/{instrument_id:path}",response_model=ApiResponse)
async def instrument(instrument_id:str):
 i=catalog.get(instrument_id)
 if not i:raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 return ApiResponse(data=i.model_dump(),meta=ApiMeta(source="instrument-catalog",freshness=Freshness.live,currency=i.quote_currency or i.currency))
@router.get("/market/quotes",response_model=ApiResponse)
async def quotes(instrument_ids:str):
 ids=list(dict.fromkeys(filter(None,instrument_ids.split(","))))[:20]; results=await asyncio.gather(*(get_quote(x) for x in ids),return_exceptions=True)
 for result in results:
  if isinstance(result,Quote):
   alerts.evaluate("local-user",result);paper_broker.process("local-user",result)
 data=[r.model_dump() if isinstance(r,Quote) else {"instrument_id":x,"price":None,"freshness":"unavailable","source":"none","as_of":datetime.now(timezone.utc)} for x,r in zip(ids,results)]
 return ApiResponse(data=data,meta=ApiMeta(source="provider-router",freshness=Freshness.live if any(str(x.get("freshness")) in {"live","Freshness.live"} for x in data) else Freshness.delayed))
@router.get("/market/candles",response_model=ApiResponse)
async def candles(instrument_id:str,timeframe:str="1d",limit:int=Query(300,ge=20,le=1000)):
 i=catalog.get(instrument_id)
 if not i:raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 try:rows=await providers.for_instrument(i).candles(i,timeframe,limit)
 except ValueError as e:raise HTTPException(400,detail={"code":"UNSUPPORTED_TIMEFRAME","message":str(e)}) from e
 except Exception as e:raise HTTPException(503,detail={"code":"PROVIDER_UNAVAILABLE","message":"Mum verisi alınamıyor","retryable":True}) from e
 return ApiResponse(data=[x.model_dump() for x in rows],meta=ApiMeta(source=providers.for_instrument(i).name,freshness=rows[-1].freshness if rows else Freshness.unavailable,currency=i.quote_currency or i.currency))
@router.get("/markets/overview",response_model=ApiResponse)
async def overview():return await quotes("crypto:binance:btcusdt,crypto:binance:ethusdt,stock:xnas:aapl,stock:xist:thyao,index:index:spx")
@router.get("/fundamentals/{instrument_id:path}",response_model=ApiResponse)
async def fundamentals(instrument_id:str):
 i=catalog.get(instrument_id)
 if not i:raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 try:data=await providers.for_instrument(i).fundamentals(i)
 except ValueError as e:raise HTTPException(404,detail={"code":"FUNDAMENTALS_UNAVAILABLE","message":str(e)}) from e
 except Exception as e:raise HTTPException(503,detail={"code":"PROVIDER_UNAVAILABLE","message":"Temel veriler alınamıyor","retryable":True}) from e
 return ApiResponse(data=data.model_dump(),meta=ApiMeta(source=data.source,freshness=data.freshness,currency=data.currency))
@router.get("/compare",response_model=ApiResponse)
async def compare(instrument_ids:str):
 ids=list(dict.fromkeys(filter(None,instrument_ids.split(","))))[:6]
 if len(ids)<2:raise HTTPException(400,detail={"code":"COMPARE_REQUIRES_TWO","message":"En az iki enstrüman gerekli"})
 qs,fs=await asyncio.gather(asyncio.gather(*(get_quote(x) for x in ids),return_exceptions=True),asyncio.gather(*(fundamentals(x) for x in ids),return_exceptions=True))
 rows=[]
 for iid,q,f in zip(ids,qs,fs):rows.append({"instrument":catalog.get(iid).model_dump() if catalog.get(iid) else None,"quote":q.model_dump() if isinstance(q,Quote) else None,"fundamentals":f.data if isinstance(f,ApiResponse) else None})
 return ApiResponse(data=rows,meta=ApiMeta(source="provider-router",freshness=Freshness.delayed))
@router.get("/financial-statements/{instrument_id:path}",response_model=ApiResponse)
async def financial_statements(instrument_id:str,frequency:str="quarterly"):
 i=catalog.get(instrument_id)
 if not i:raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 if frequency not in {"quarterly","annual"}:raise HTTPException(400,detail={"code":"INVALID_FREQUENCY","message":"quarterly veya annual kullanın"})
 try:rows=await providers.for_instrument(i).statements(i,frequency)
 except ValueError as e:raise HTTPException(404,detail={"code":"STATEMENTS_UNAVAILABLE","message":str(e)}) from e
 except Exception as e:raise HTTPException(503,detail={"code":"PROVIDER_UNAVAILABLE","message":"Finansal tablolar alınamıyor"}) from e
 return ApiResponse(data=[x.model_dump() for x in rows],meta=ApiMeta(source=providers.for_instrument(i).name,freshness=Freshness.delayed,currency=i.currency))
@router.get("/corporate-actions/{instrument_id:path}",response_model=ApiResponse)
async def corporate_actions(instrument_id:str):
 i=catalog.get(instrument_id)
 if not i:raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 try:rows=await providers.for_instrument(i).actions(i)
 except Exception as e:raise HTTPException(503,detail={"code":"PROVIDER_UNAVAILABLE","message":"Kurumsal aksiyonlar alınamıyor"}) from e
 return ApiResponse(data=[x.model_dump() for x in rows],meta=ApiMeta(source=providers.for_instrument(i).name,freshness=Freshness.delayed,currency=i.currency))
@router.get("/calendar",response_model=ApiResponse)
async def calendar(instrument_id:str):
 i=catalog.get(instrument_id)
 if not i:raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 try:rows=await events_for(i)
 except Exception as e:raise HTTPException(503,detail={"code":"CALENDAR_UNAVAILABLE","message":"Takvim verisi alınamıyor","retryable":True}) from e
 return ApiResponse(data=rows,meta=ApiMeta(source="yfinance" if rows else "none",freshness=Freshness.delayed if rows else Freshness.unavailable,currency=i.currency))
@router.get("/filings/{instrument_id:path}",response_model=ApiResponse)
async def filings(instrument_id:str,limit:int=Query(20,ge=1,le=100)):
 i=catalog.get(instrument_id)
 if not i:raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 if i.mic=="XIST":return ApiResponse(data=[{"instrument_id":i.id,"source":"KAP","url":f"https://www.kap.org.tr/tr/sirket-bilgileri/ozet/{i.symbol}","status":"official_index"}],meta=ApiMeta(source="KAP",freshness=Freshness.delayed,currency=i.currency))
 try:rows=await sec_filings(i,limit)
 except Exception as e:raise HTTPException(503,detail={"code":"FILINGS_UNAVAILABLE","message":"Resmî bildirimler alınamıyor","retryable":True}) from e
 return ApiResponse(data=rows,meta=ApiMeta(source="SEC EDGAR" if rows else "none",freshness=Freshness.delayed if rows else Freshness.unavailable,currency=i.currency))
@router.get("/news/{instrument_id:path}",response_model=ApiResponse)
async def instrument_news(instrument_id:str,limit:int=Query(12,ge=1,le=30)):
 i=catalog.get(instrument_id)
 if not i:raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 try:rows=await news_for(i,limit)
 except Exception as e:raise HTTPException(503,detail={"code":"NEWS_UNAVAILABLE","message":"Haber akışı alınamıyor","retryable":True}) from e
 return ApiResponse(data=[x.model_dump() for x in rows],meta=ApiMeta(source="google-news-rss",freshness=Freshness.delayed))
@router.get("/analysis/{instrument_id:path}",response_model=ApiResponse)
async def analysis(instrument_id:str,timeframe:str="1d"):
 i=catalog.get(instrument_id)
 if not i:raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 try:rows=await providers.for_instrument(i).candles(i,timeframe,250);data=technical_snapshot(rows);alerts.evaluate_snapshot("local-user",instrument_id,data)
 except ValueError as e:raise HTTPException(422,detail={"code":"INSUFFICIENT_HISTORY","message":str(e)}) from e
 return ApiResponse(data=data,meta=ApiMeta(source=providers.for_instrument(i).name,freshness=rows[-1].freshness,currency=i.quote_currency or i.currency))
@router.get("/research/summary/{instrument_id:path}",response_model=ApiResponse)
async def research_summary(instrument_id:str):
 i=catalog.get(instrument_id)
 if not i:raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 facts=None;snapshot=None
 try:facts=(await providers.for_instrument(i).fundamentals(i)).model_dump(mode="json")
 except Exception:pass
 try:snapshot=technical_snapshot(await providers.for_instrument(i).candles(i,"1d",250))
 except Exception:pass
 data=await summarize(i,facts,snapshot);data.update({"instrument_id":i.id,"facts_as_of":facts.get("as_of") if facts else None,"formula_version":"technical-v1"})
 return ApiResponse(data=data,meta=ApiMeta(source=data["model"],freshness=Freshness.delayed,currency=i.quote_currency or i.currency))
@router.post("/paper/orders",response_model=ApiResponse)
async def order(body:PaperOrderIn,authorization:str|None=Header(default=None)):
 user=await uid(authorization);await hydrate_paper(user);q=await get_quote(body.instrument_id);before={x.id for x in paper_broker.orders[user]};row=paper_broker.submit(user,body,q);i=catalog.get(body.instrument_id)
 await persist_paper_events(user,[x for x in paper_broker.orders[user] if x.id not in before])
 await repository.upsert("paper_accounts",{"id":row.account_id,"user_id":user,"name":"Primary Paper","base_currency":"USD","starting_cash":paper_broker.starting_cash,"cash_balance":paper_broker.cash[user]})
 holding=paper_broker.holdings[user].get(body.instrument_id);await repository.sync_position(user,row.account_id,body.instrument_id,{"quantity":holding[0],"average_price":holding[1]} if holding else None)
 return ApiResponse(data=row.model_dump(),meta=ApiMeta(source="paper-engine",freshness=q.freshness,currency=i.quote_currency or i.currency))
@router.get("/paper/orders",response_model=ApiResponse)
async def orders(cursor:str|None=None,limit:int=Query(50,ge=1,le=200),authorization:str|None=Header(default=None)):
 user=await uid(authorization);stored=await repository.list("paper_orders",user);rows=stored if stored is not None else [x.model_dump() for x in reversed(paper_broker.orders[user])];data,next_cursor=cursor_page(rows,cursor,limit);return ApiResponse(data=data,meta=ApiMeta(source="paper-engine",freshness=Freshness.live,next_cursor=next_cursor))
@router.get("/paper/fills",response_model=ApiResponse)
async def fills(authorization:str|None=Header(default=None)):
 user=await uid(authorization);stored=await repository.list("paper_fills",user,"filled_at");return ApiResponse(data=stored if stored is not None else list(reversed(paper_broker.fills[user])),meta=ApiMeta(source="paper-engine",freshness=Freshness.live))
@router.get("/paper/cash-ledger",response_model=ApiResponse)
async def cash_ledger(authorization:str|None=Header(default=None)):
 user=await uid(authorization);stored=await repository.list("cash_ledger",user,"created_at");return ApiResponse(data=stored if stored is not None else list(reversed(paper_broker.cash_ledger[user])),meta=ApiMeta(source="paper-engine",freshness=Freshness.live))
@router.delete("/paper/orders/{order_id}",response_model=ApiResponse)
async def cancel_order(order_id:str,authorization:str|None=Header(default=None)):
 row=paper_broker.cancel(await uid(authorization),order_id)
 if not row:raise HTTPException(409,detail={"code":"ORDER_NOT_CANCELLABLE","message":"Emir iptal edilemez"})
 await repository.upsert("paper_orders",row.model_dump(mode="json"))
 return ApiResponse(data=row.model_dump(),meta=ApiMeta(source="paper-engine",freshness=Freshness.live))
@router.get("/paper/positions",response_model=ApiResponse)
async def positions(authorization:str|None=Header(default=None)):
 user=await uid(authorization)
 await hydrate_paper(user)
 ids=list(paper_broker.holdings[user]); results=await asyncio.gather(*(get_quote(x) for x in ids),return_exceptions=True); q={x:r for x,r in zip(ids,results) if isinstance(r,Quote)}
 return ApiResponse(data=[x.model_dump() for x in paper_broker.positions(user,q)],meta=ApiMeta(source="paper-engine",freshness=Freshness.live))
@router.post("/portfolios/transactions",response_model=ApiResponse)
async def add_transaction(body:PortfolioTransactionIn,authorization:str|None=Header(default=None)):
 if not catalog.get(body.instrument_id):raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 user=await uid(authorization);row=portfolio_engine.add(user,body);await repository.upsert("portfolio_transactions",row)
 return ApiResponse(data=row,meta=ApiMeta(source="portfolio-engine",freshness=Freshness.live,currency=body.currency))
@router.get("/portfolios/summary",response_model=ApiResponse)
async def portfolio_summary(base_currency:str="USD",authorization:str|None=Header(default=None)):
 user=await uid(authorization)
 if repository.enabled and not portfolio_engine.transactions[user]:portfolio_engine.transactions[user]=await repository.list("portfolio_transactions",user,"executed_at",False) or []
 holdings=portfolio_engine.holdings(user);ids=list(holdings);results=await asyncio.gather(*(get_quote(x) for x in ids),return_exceptions=True);quote_map={x:r for x,r in zip(ids,results) if isinstance(r,Quote)}
 currencies={((catalog.get(x).quote_currency or catalog.get(x).currency)) for x in ids};fx={base_currency:1.,"USDT":1. if base_currency=="USD" else None}
 if base_currency=="USD" and "TRY" in currencies:
  try:
   import yfinance as yf;frame=await asyncio.to_thread(yf.Ticker("TRY=X").history,period="5d");fx["TRY"]=1/float(frame.Close.iloc[-1])
  except Exception:fx["TRY"]=None
 data=portfolio_engine.summary(user,quote_map,fx,base_currency)
 portfolio_engine.snapshot(user,data)
 return ApiResponse(data=data,meta=ApiMeta(source="portfolio-engine",freshness=Freshness.delayed,currency=base_currency))
@router.get("/portfolios/risk",response_model=ApiResponse)
async def portfolio_risk_api(benchmark_id:str="index:index:spx",authorization:str|None=Header(default=None)):
 user=await uid(authorization);holdings=portfolio_engine.holdings(user);ids=list(holdings)
 results=await asyncio.gather(*(providers.for_instrument(catalog.get(x)).candles(catalog.get(x),"1d",260) for x in ids),return_exceptions=True);series={x:[c.close for c in r] for x,r in zip(ids,results) if isinstance(r,list)};weights={x:holdings[x][0]*series[x][-1] for x in series};benchmark=None
 try:benchmark=[c.close for c in await providers.for_instrument(catalog.get(benchmark_id)).candles(catalog.get(benchmark_id),"1d",260)]
 except Exception:pass
 return ApiResponse(data=portfolio_risk(series,weights,benchmark),meta=ApiMeta(source="risk-engine",freshness=Freshness.delayed))
@router.get("/portfolios/performance",response_model=ApiResponse)
async def portfolio_performance(base_currency:str="USD",authorization:str|None=Header(default=None)):
 user=await uid(authorization);summary=(await portfolio_summary(base_currency,authorization)).data;transactions=portfolio_engine.transactions[user]
 data={**performance(transactions,summary["total_value"]),"time_weighted_return_pct":time_weighted_return(portfolio_engine.snapshots[user]),"twr_status":"ready" if len(portfolio_engine.snapshots[user])>1 else "requires_two_snapshots","stress":stress(summary["positions"],{"crypto":-.30,"stock":-.15,"etf":-.12,"index":-.10,"fx":-.08,"commodity":-.12,"default":-.10})}
 return ApiResponse(data=data,meta=ApiMeta(source="portfolio-analytics",freshness=Freshness.delayed,currency=base_currency))
@router.post("/screeners/saved",response_model=ApiResponse)
async def save_screen(body:SavedScreenIn,authorization:str|None=Header(default=None)):
 row=screens.create(await uid(authorization),body);await repository.upsert("saved_screens",row.model_dump(mode="json"));return ApiResponse(data=row.model_dump(),meta=ApiMeta(source="screener",freshness=Freshness.live))
@router.get("/screeners/saved",response_model=ApiResponse)
async def saved_screens(authorization:str|None=Header(default=None)):
 user=await uid(authorization);stored=await repository.list("saved_screens",user);data=stored if stored is not None else [x.model_dump() for x in screens.items[user]];return ApiResponse(data=data,meta=ApiMeta(source="screener",freshness=Freshness.live))
@router.delete("/screeners/saved/{screen_id}",status_code=204)
async def delete_screen(screen_id:str,authorization:str|None=Header(default=None)):
 user=await uid(authorization);local=screens.delete(user,screen_id)
 if repository.enabled:await repository.delete("saved_screens",user,screen_id)
 elif not local:raise HTTPException(404,detail={"code":"SCREEN_NOT_FOUND","message":"Tarama bulunamadı"})
 return Response(status_code=204)
@router.get("/providers/health",response_model=ApiResponse)
async def health():return ApiResponse(data=[*await asyncio.gather(*(x.health() for x in providers.providers.values())),await quote_cache.health(),await repository.health()],meta=ApiMeta(source="provider-router",freshness=Freshness.live))
@router.get("/data-quality",response_model=ApiResponse)
async def data_quality():
 health_rows=[*await asyncio.gather(*(x.health() for x in providers.providers.values())),await quote_cache.health(),await repository.health()]
 instruments=list(catalog.items.values());capabilities={name:sum(name in x.data_capabilities for x in instruments) for name in {c for x in instruments for c in x.data_capabilities}}
 unavailable=[x for x in health_rows if x.get("status") not in {"ok","disabled"}]
 return ApiResponse(data={"status":"degraded" if unavailable else "healthy","providers":health_rows,"instrument_count":len(instruments),"capability_coverage":capabilities,"issues":unavailable,"policy":{"missing_data":"never_estimate","stale_market_orders":"rejected","free_data_sla":False}},meta=ApiMeta(source="quality-monitor",freshness=Freshness.live))
@router.get("/workspaces",response_model=ApiResponse)
async def list_workspaces(authorization:str|None=Header(default=None)):
 user=await uid(authorization);stored=await repository.list("workspace_layouts",user,"updated_at")
 data=stored if stored else [x.model_dump() for x in workspaces.defaults(user)]
 return ApiResponse(data=data,meta=ApiMeta(source="workspace-store",freshness=Freshness.live))
@router.post("/workspaces",response_model=ApiResponse)
async def create_workspace(body:WorkspaceIn,authorization:str|None=Header(default=None)):
 row=workspaces.save(await uid(authorization),body);await repository.upsert("workspace_layouts",row.model_dump(mode="json"))
 return ApiResponse(data=row.model_dump(),meta=ApiMeta(source="workspace-store",freshness=Freshness.live))
@router.put("/workspaces/{workspace_id}",response_model=ApiResponse)
async def update_workspace(workspace_id:str,body:WorkspaceIn,authorization:str|None=Header(default=None)):
 user=await uid(authorization);workspaces.defaults(user);row=workspaces.update(user,workspace_id,body)
 if not row:raise HTTPException(404,detail={"code":"WORKSPACE_NOT_FOUND","message":"Çalışma alanı bulunamadı"})
 await repository.upsert("workspace_layouts",row.model_dump(mode="json"));return ApiResponse(data=row.model_dump(),meta=ApiMeta(source="workspace-store",freshness=Freshness.live))
@router.get("/screeners",response_model=ApiResponse)
async def screener(asset_class:str|None=None,exchange:str|None=None,min_price:float|None=None,max_price:float|None=None,min_change_pct:float|None=None,max_change_pct:float|None=None,min_rsi:float|None=None,max_rsi:float|None=None,min_relative_volume:float|None=None,sort:str="change_pct",direction:str="desc",include_technical:bool=False,limit:int=Query(30,ge=1,le=100)):
 universe=[x for x in catalog.items.values() if (not asset_class or x.asset_class.value==asset_class) and (not exchange or x.exchange==exchange)][:limit];results=await asyncio.gather(*(get_quote(x.id) for x in universe),return_exceptions=True);available=[x for x in results if isinstance(x,Quote)];rows=screen(available,asset_class,exchange,min_price,max_price,min_change_pct,max_change_pct,sort,direction)
 if include_technical and rows:
  histories=await asyncio.gather(*(providers.for_instrument(catalog.get(x["instrument"]["id"])).candles(catalog.get(x["instrument"]["id"]),"1d",80) for x in rows),return_exceptions=True);enriched=[]
  for row,history in zip(rows,histories):
   try:tech=technical_snapshot(history) if isinstance(history,list) else None
   except ValueError:tech=None
   if min_rsi is not None and (not tech or tech["rsi"]<min_rsi):continue
   if max_rsi is not None and (not tech or tech["rsi"]>max_rsi):continue
   if min_relative_volume is not None and (not tech or tech["relative_volume"] is None or tech["relative_volume"]<min_relative_volume):continue
   row["technical"]=tech;enriched.append(row)
  rows=enriched
 return ApiResponse(data=rows,meta=ApiMeta(source="provider-router",freshness=Freshness.delayed))
@router.post("/alerts",response_model=ApiResponse)
async def create_alert(body:AlertIn,authorization:str|None=Header(default=None)):
 if not catalog.get(body.instrument_id):raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 row=alerts.create(await uid(authorization),body);await repository.upsert("alerts_v3",row.model_dump(mode="json"));return ApiResponse(data=row.model_dump(),meta=ApiMeta(source="alert-engine",freshness=Freshness.live))
@router.get("/alerts",response_model=ApiResponse)
async def list_alerts(cursor:str|None=None,limit:int=Query(50,ge=1,le=200),authorization:str|None=Header(default=None)):
 user=await uid(authorization);stored=await repository.list("alerts_v3",user);rows=stored if stored is not None else [x.model_dump() for x in alerts.items[user]];data,next_cursor=cursor_page(rows,cursor,limit);return ApiResponse(data=data,meta=ApiMeta(source="alert-engine",freshness=Freshness.live,next_cursor=next_cursor))
@router.delete("/alerts/{alert_id}",status_code=204)
async def delete_alert(alert_id:str,authorization:str|None=Header(default=None)):
 user=await uid(authorization);local=alerts.delete(user,alert_id)
 if repository.enabled:await repository.delete("alerts_v3",user,alert_id)
 elif not local:raise HTTPException(404,detail={"code":"ALERT_NOT_FOUND","message":"Alarm bulunamadı"})
 return Response(status_code=204)
@router.get("/alert-events",response_model=ApiResponse)
async def alert_events(authorization:str|None=Header(default=None)):
 user=await uid(authorization);return ApiResponse(data=list(reversed(alerts.events[user])),meta=ApiMeta(source="alert-engine",freshness=Freshness.live))
@router.post("/research/notes",response_model=ApiResponse)
async def create_note(body:JournalEntryIn,authorization:str|None=Header(default=None)):
 row=journal.create(await uid(authorization),body);await repository.upsert("research_notes",row.model_dump(mode="json"));return ApiResponse(data=row.model_dump(),meta=ApiMeta(source="journal",freshness=Freshness.live))
@router.get("/research/notes",response_model=ApiResponse)
async def list_notes(cursor:str|None=None,limit:int=Query(50,ge=1,le=200),authorization:str|None=Header(default=None)):
 user=await uid(authorization);stored=await repository.list("research_notes",user);rows=stored if stored is not None else [x.model_dump() for x in reversed(journal.items[user])];data,next_cursor=cursor_page(rows,cursor,limit);return ApiResponse(data=data,meta=ApiMeta(source="journal",freshness=Freshness.live,next_cursor=next_cursor))
@router.put("/research/notes/{entry_id}",response_model=ApiResponse)
async def update_note(entry_id:str,body:JournalEntryIn,authorization:str|None=Header(default=None)):
 row=journal.update(await uid(authorization),entry_id,body)
 if not row:raise HTTPException(404,detail={"code":"NOTE_NOT_FOUND","message":"Not bulunamadı"})
 await repository.upsert("research_notes",row.model_dump(mode="json"))
 return ApiResponse(data=row.model_dump(),meta=ApiMeta(source="journal",freshness=Freshness.live))
@router.delete("/research/notes/{entry_id}",status_code=204)
async def delete_note(entry_id:str,authorization:str|None=Header(default=None)):
 user=await uid(authorization);local=journal.delete(user,entry_id)
 if repository.enabled:await repository.delete("research_notes",user,entry_id)
 elif not local:raise HTTPException(404,detail={"code":"NOTE_NOT_FOUND","message":"Not bulunamadı"})
 return Response(status_code=204)
@router.get("/backtests",response_model=ApiResponse)
async def backtests(instrument_id:str,strategy:str="ma_cross",timeframe:str="1d",fast:int=20,slow:int=50):
 i=catalog.get(instrument_id)
 if not i:raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 try:rows=await providers.for_instrument(i).candles(i,timeframe,1000); result=run_backtest(rows,strategy,fast,slow)
 except ValueError as e:raise HTTPException(400,detail={"code":"INVALID_BACKTEST","message":str(e)}) from e
 except Exception as e:raise HTTPException(503,detail={"code":"PROVIDER_UNAVAILABLE","message":"Backtest verisi alınamıyor"}) from e
 return ApiResponse(data=result,meta=ApiMeta(source=providers.for_instrument(i).name,freshness=rows[-1].freshness,currency=i.quote_currency or i.currency))
@router.get("/backtests/optimize",response_model=ApiResponse)
async def backtest_optimize(instrument_id:str,strategy:str="ma_cross",timeframe:str="1d"):
 i=catalog.get(instrument_id)
 if not i:raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 rows=await providers.for_instrument(i).candles(i,timeframe,1000);result=optimize_backtest(rows,strategy)
 return ApiResponse(data=result,meta=ApiMeta(source=providers.for_instrument(i).name,freshness=rows[-1].freshness,currency=i.quote_currency or i.currency))
@router.get("/backtests/walk-forward",response_model=ApiResponse)
async def backtest_walk_forward(instrument_id:str,strategy:str="ma_cross",timeframe:str="1d",train_bars:int=252,test_bars:int=63):
 i=catalog.get(instrument_id)
 if not i:raise HTTPException(404,detail={"code":"INSTRUMENT_NOT_FOUND","message":"Enstrüman bulunamadı"})
 rows=await providers.for_instrument(i).candles(i,timeframe,1000);result=walk_forward(rows,strategy,train_bars,test_bars)
 return ApiResponse(data=result,meta=ApiMeta(source=providers.for_instrument(i).name,freshness=rows[-1].freshness,currency=i.quote_currency or i.currency))
@router.get("/journal/analytics",response_model=ApiResponse)
async def journal_analytics(authorization:str|None=Header(default=None)):
 user=await uid(authorization);stored=await repository.list("paper_orders",user);data=stored if stored is not None else paper_broker.orders[user]
 return ApiResponse(data=summarize_orders(data),meta=ApiMeta(source="journal-analytics",freshness=Freshness.live))
@router.get("/brokers/capabilities",response_model=ApiResponse)
async def broker_capabilities():return ApiResponse(data={"adapter":live_broker.name,**live_broker.capabilities.__dict__},meta=ApiMeta(source="broker-router",freshness=Freshness.live))
@router.websocket("/ws/market/{instrument_id:path}")
async def stream(ws:WebSocket,instrument_id:str,token:str|None=None):
 await ws.accept()
 try:user=(await authenticate(f"Bearer {token}" if token else None)).user_id
 except HTTPException:await ws.send_json({"error":{"code":"AUTH_REQUIRED"}});await ws.close(code=1008);return
 instrument=catalog.get(instrument_id)
 if not instrument:await ws.send_json({"error":{"code":"INSTRUMENT_NOT_FOUND"}});await ws.close(code=1008);return
 try:
  if "binance" in instrument.provider_symbols:
   book=DepthBook();book.snapshot(await depth_snapshot(instrument))
   async for event in binance_events(instrument):
    if event["type"]=="trade":
     live_quote=Quote(instrument_id=instrument.id,price=event["price"],source="binance-ws",freshness=Freshness.live,as_of=datetime.fromtimestamp(event["event_time"]/1000,tz=timezone.utc),market_status="open")
     triggered=alerts.evaluate(user,live_quote);changed=paper_broker.process(user,live_quote,event.get("quantity"))
     if changed:await persist_paper_events(user,changed)
     if triggered:await ws.send_text(json.dumps({"topic":f"alerts:{user}","data":triggered},default=str))
     if changed:await ws.send_text(json.dumps({"topic":f"paper:paper:{user}","data":[x.model_dump(mode="json") for x in changed]},default=str))
    if event["type"]=="depth":
     state=book.apply(event)
     if state=="gap":book.snapshot(await depth_snapshot(instrument));state="resynced"
     event={"type":"depth","instrument_id":instrument.id,"state":state,**book.top()}
    await ws.send_text(json.dumps({"topic":f"{event['type']}:{instrument_id}","data":event}))
  else:
   while True:
    try:q=await get_quote(instrument_id);await ws.send_text(json.dumps({"topic":f"quote:{instrument_id}","data":q.model_dump(mode="json")}))
    except HTTPException as e:await ws.send_json({"topic":f"quote:{instrument_id}","error":e.detail})
    await asyncio.sleep(30)
 except WebSocketDisconnect:return
 except Exception as e:
  await ws.send_json({"error":{"code":"STREAM_UNAVAILABLE","message":type(e).__name__}});await ws.close(code=1011)
