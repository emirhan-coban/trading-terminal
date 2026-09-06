from __future__ import annotations

import asyncio,hashlib,json,os,sqlite3
from dataclasses import asdict,dataclass
from datetime import datetime,timezone
from pathlib import Path

from .catalog import catalog
from .models import PaperOrderIn
from .okx_broker import okx_demo_broker
from .paper import paper_broker
from .providers import providers


@dataclass(frozen=True)
class BotConfig:
    instrument_id:str="crypto:okx:btc-usdt"
    timeframe:str="1m"
    fast:int=3
    slow:int=8
    max_allocation:float=.10
    risk_per_trade:float=.0005
    stop_loss_pct:float=.005
    take_profit_pct:float=.0035
    mode:str="paper"
    poll_seconds:int=10


class BotStore:
    def __init__(self,path=None):
        default=Path(__file__).parents[1]/"data"/"nexus_bot.sqlite3"
        configured=Path(path or os.getenv("BOT_DB_PATH",default))
        if str(configured).startswith("/app/") and not Path("/app").exists():configured=default
        self.path=configured;self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path,check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        self.db.executescript("""
        pragma journal_mode=WAL;
        create table if not exists bot_state (bot_id text primary key, config text not null, status text not null, last_candle text, position real not null default 0, entry_price real, cash real not null default 100000, heartbeat text, error text, protective_order_id text, equity_day text, day_start_equity real);
        create table if not exists bot_events (id integer primary key autoincrement, bot_id text not null, candle_time text, kind text not null, payload text not null, created_at text not null, unique(bot_id,candle_time,kind));
        """)
        columns={x[1] for x in self.db.execute("pragma table_info(bot_state)")}
        for name,kind in (("protective_order_id","text"),("equity_day","text"),("day_start_equity","real")):
            if name not in columns:self.db.execute(f"alter table bot_state add column {name} {kind}")
        self.db.commit()
    def ensure(self,bot_id,config):
        encoded=json.dumps(asdict(config))
        current=self.db.execute("select config from bot_state where bot_id=?",(bot_id,)).fetchone()
        changed=bool(current and current["config"]!=encoded)
        self.db.execute("insert into bot_state(bot_id,config,status) values(?,?,?) on conflict(bot_id) do update set config=excluded.config",(bot_id,encoded,"stopped"))
        if changed:self.db.execute("update bot_state set last_candle=null,equity_day=null,day_start_equity=null,error=null where bot_id=?",(bot_id,))
        self.db.commit()
    def state(self,bot_id):
        row=self.db.execute("select * from bot_state where bot_id=?",(bot_id,)).fetchone();return dict(row) if row else None
    def status(self,bot_id,status,error=None):
        self.db.execute("update bot_state set status=?,heartbeat=?,error=? where bot_id=?",(status,datetime.now(timezone.utc).isoformat(),error,bot_id));self.db.commit()
    def record(self,bot_id,candle_time,kind,payload,position,cash,entry_price=None,protective_order_id=None,equity_day=None,day_start_equity=None):
        try:self.db.execute("insert into bot_events(bot_id,candle_time,kind,payload,created_at) values(?,?,?,?,?)",(bot_id,candle_time,kind,json.dumps(payload),datetime.now(timezone.utc).isoformat()))
        except sqlite3.IntegrityError:self.db.rollback();return False
        self.db.execute("update bot_state set last_candle=?,position=?,entry_price=?,cash=?,heartbeat=?,error=null,protective_order_id=?,equity_day=?,day_start_equity=? where bot_id=?",(candle_time,position,entry_price,cash,datetime.now(timezone.utc).isoformat(),protective_order_id,equity_day,day_start_equity,bot_id));self.db.commit();return True
    def events(self,bot_id,limit=100):return [dict(x) for x in self.db.execute("select * from bot_events where bot_id=? order by id desc limit ?",(bot_id,limit))]
    def resumable(self):return [dict(x) for x in self.db.execute("select * from bot_state where status='running'")]


class BotService:
    def __init__(self,store=None):self.store=store or BotStore();self.tasks={};self.preserve_running=set()
    @staticmethod
    def signal(candles,fast,slow):
        closed=[x for x in candles if "open_candle" not in x.quality_flags]
        if len(closed)<slow+1:return None,None
        current=closed
        new_fast=sum(x.close for x in current[-fast:])/fast;new_slow=sum(x.close for x in current[-slow:])/slow
        action="buy" if new_fast>new_slow else "sell" if new_fast<new_slow else "hold"
        return action,closed[-1]
    async def step(self,bot_id,config):
        instrument=catalog.get(config.instrument_id)
        if not instrument:raise ValueError("Unknown bot instrument")
        provider=providers.for_instrument(instrument)
        candles,quote=await asyncio.gather(asyncio.wait_for(provider.candles(instrument,config.timeframe,max(100,config.slow+2)),timeout=15),asyncio.wait_for(provider.quote(instrument),timeout=15));action,candle=self.signal(candles,config.fast,config.slow)
        if candle is None:return
        state=self.store.state(bot_id);position=float(state["position"]);entry_price=float(state["entry_price"] or 0);cash=float(state["cash"]);protective=state["protective_order_id"]
        if position>0 and not entry_price:
            position=0
            protective=None
        if config.mode=="okx_demo":
            balances=await okx_demo_broker.balances((instrument.quote_currency,));cash=balances.get(instrument.quote_currency,0)
            if position==0:entry_price=0;protective=None
        price=float(quote.price);stop_hit=position>0 and entry_price and price<=entry_price*(1-config.stop_loss_pct)
        take_profit_hit=position>0 and entry_price and price>=entry_price*(1+config.take_profit_pct)
        if stop_hit and config.mode=="paper":action="sell"
        if take_profit_hit:action="sell"
        day=datetime.now(timezone.utc).date().isoformat();equity=cash+position*price
        day_start=equity if state["equity_day"]!=day or state["day_start_equity"] is None else float(state["day_start_equity"])
        daily_loss=(equity/day_start-1) if day_start else 0
        if daily_loss<=-.01 and action=="buy":action="hold";reason="daily_loss_limit"
        else:reason="take_profit" if take_profit_hit else "stop_loss" if stop_hit else "ma_trend"
        payload={"action":action,"price":price,"fast":config.fast,"slow":config.slow,"mode":config.mode,"reason":reason,"equity":round(equity,4),"daily_pnl_pct":round(daily_loss*100,4)}
        candle_time=candle.open_time.isoformat()
        if not self.store.record(bot_id,candle_time,"decision",payload,position,cash,entry_price or None,protective,day,day_start):return
        executed=False
        if action=="buy" and position==0:
            allocation=min(cash*config.max_allocation,cash*config.risk_per_trade/config.stop_loss_pct)
            quantity=allocation/price
            order=PaperOrderIn(instrument_id=config.instrument_id,side="buy",quantity=quantity)
            if config.mode=="okx_demo":
                client_id=self._client_id(bot_id,candle_time,"buy");payload["order"]=await okx_demo_broker.submit(bot_id,order,client_order_id=client_id)
                if payload["order"]["status"]!="filled":raise RuntimeError(f"OKX_ORDER_{payload['order']['status']}")
                quantity=payload["order"]["filled_quantity"];price=payload["order"]["fill_price"]
                stop_id=self._client_id(bot_id,candle_time,"stop");stop=await okx_demo_broker.place_stop(instrument.provider_symbols["okx"],quantity,round(price*(1-config.stop_loss_pct),instrument.price_precision),stop_id);protective=stop["algo_id"];payload["protective_stop"]=stop
                balances=await okx_demo_broker.balances((instrument.quote_currency,));cash=balances.get(instrument.quote_currency,cash)
            else:
                quote=await providers.for_instrument(instrument).quote(instrument);result=paper_broker.submit(bot_id,order,quote)
                if result.status!="filled":raise RuntimeError(result.rejection_reason or "PAPER_ORDER_REJECTED")
                quantity=result.filled_quantity;price=result.fill_price;cash-=price*quantity+result.commission
            position=quantity
            entry_price=price
            executed=True
        elif action=="sell" and position>0:
            order=PaperOrderIn(instrument_id=config.instrument_id,side="sell",quantity=position)
            if config.mode=="okx_demo":
                if protective:await okx_demo_broker.cancel_stop(instrument.provider_symbols["okx"],protective)
                client_id=self._client_id(bot_id,candle_time,"sell");payload["order"]=await okx_demo_broker.submit(bot_id,order,client_order_id=client_id)
                if payload["order"]["status"]!="filled":raise RuntimeError(f"OKX_ORDER_{payload['order']['status']}")
                balances=await okx_demo_broker.balances((instrument.quote_currency,instrument.currency));cash=balances.get(instrument.quote_currency,cash)
            else:
                quote=await providers.for_instrument(instrument).quote(instrument);result=paper_broker.submit(bot_id,order,quote)
                if result.status!="filled":raise RuntimeError(result.rejection_reason or "PAPER_ORDER_REJECTED")
                cash+=result.fill_price*result.filled_quantity-result.commission
            position=0
            entry_price=0
            protective=None
            executed=True
        if executed:self.store.record(bot_id,candle_time,"execution",payload,position,cash,entry_price or None,protective,day,day_start)
    @staticmethod
    def _client_id(bot_id,candle_time,side):return "nx"+hashlib.sha256(f"{bot_id}|{candle_time}|{side}".encode()).hexdigest()[:28]
    async def run(self,bot_id,config):
        self.store.status(bot_id,"running")
        while True:
            try:await self.step(bot_id,config);self.store.status(bot_id,"running")
            except asyncio.CancelledError:
                if bot_id not in self.preserve_running:self.store.status(bot_id,"stopped")
                raise
            except Exception as error:self.store.status(bot_id,"error",f"{type(error).__name__}: {error}")
            await asyncio.sleep(config.poll_seconds)
    def start(self,bot_id="okx-btc-1h",config=None):
        config=config or BotConfig()
        if config.mode not in {"paper","okx_demo"}:raise RuntimeError("INVALID_BOT_MODE")
        if config.mode=="okx_demo" and not okx_demo_broker.configured:raise RuntimeError("OKX_DEMO_NOT_CONFIGURED")
        if bot_id in self.tasks and not self.tasks[bot_id].done():return self.store.state(bot_id)
        self.store.ensure(bot_id,config);self.store.status(bot_id,"running");self.tasks[bot_id]=asyncio.create_task(self.run(bot_id,config))
        return self.store.state(bot_id)
    def stop(self,bot_id):
        task=self.tasks.pop(bot_id,None)
        if task:task.cancel()
        self.store.status(bot_id,"stopped");return self.store.state(bot_id)
    def resume(self):
        resumed=[]
        for state in self.store.resumable():
            config=BotConfig(**json.loads(state["config"]))
            if config.mode=="okx_demo" and not okx_demo_broker.configured:
                self.store.status(state["bot_id"],"error","OKX_DEMO_NOT_CONFIGURED");continue
            self.tasks[state["bot_id"]]=asyncio.create_task(self.run(state["bot_id"],config));resumed.append(state["bot_id"])
        return resumed
    def shutdown(self):
        self.preserve_running.update(self.tasks)
        for task in self.tasks.values():task.cancel()
        self.tasks.clear()


bot_service=BotService()
