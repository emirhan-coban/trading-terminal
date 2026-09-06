import asyncio,json
from datetime import datetime,timedelta,timezone

from terminal.bot import BotConfig,BotService,BotStore
from terminal.models import Candle,Freshness,PaperOrderIn
from terminal.okx_broker import OkxDemoBroker


def candle(n,price,open_flag=False):
    return Candle(instrument_id="crypto:okx:btc-usdt",timeframe="1h",open_time=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(hours=n),open=price,high=price,low=price,close=price,volume=1,source="test",freshness=Freshness.live,quality_flags=["open_candle"] if open_flag else [])


def test_bot_signal_ignores_open_candle():
    rows=[candle(n,100-n) for n in range(51)]+[candle(51,1000,True)]
    action,last=BotService.signal(rows,20,50)
    assert action=="sell"
    assert last.open_time==rows[-2].open_time


def test_scalping_defaults_use_closed_one_minute_candles():
    config=BotConfig()
    assert (config.timeframe,config.fast,config.slow)==("1m",3,8)
    assert config.poll_seconds==10
    assert config.take_profit_pct==.0035


def test_store_deduplicates_a_decision(tmp_path):
    store=BotStore(tmp_path/"bot.sqlite3");store.ensure("bot",BotConfig())
    assert store.record("bot","2026-01-01T00:00:00Z","decision",{"action":"hold"},0,100000)
    assert not store.record("bot","2026-01-01T00:00:00Z","decision",{"action":"buy"},0,100000)


def test_store_resets_daily_baseline_when_strategy_changes(tmp_path):
    store=BotStore(tmp_path/"bot.sqlite3");store.ensure("bot",BotConfig())
    store.record("bot","2026-01-01T00:00:00Z","decision",{"action":"hold"},0,100000,equity_day="2026-01-01",day_start_equity=100000)
    store.ensure("bot",BotConfig(fast=4))
    state=store.state("bot")
    assert state["last_candle"] is None
    assert state["equity_day"] is None
    assert state["day_start_equity"] is None


def test_okx_demo_request_always_sets_simulation_header(monkeypatch):
    seen={}
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self):return json.dumps({"code":"0","data":[]}).encode()
    def fake(request,timeout):seen.update(dict(request.header_items()));return Response()
    monkeypatch.setattr("terminal.okx_broker.urlopen",fake)
    broker=OkxDemoBroker("key","secret","pass")
    broker._request("GET","/api/v5/account/balance")
    assert seen["X-simulated-trading"]=="1"
    assert "Ok-access-sign" in seen


def test_okx_demo_is_not_live_money():
    assert not OkxDemoBroker.capabilities.live_money


def test_okx_regional_base_is_configurable():
    broker=OkxDemoBroker("key","secret","pass",base_url="https://tr.okx.com/")
    assert broker.base=="https://tr.okx.com"


def test_okx_rejects_unknown_base():
    import pytest
    with pytest.raises(ValueError,match="BASE_URL_NOT_ALLOWED"):
        OkxDemoBroker("key","secret","pass",base_url="https://example.com")


def test_okx_size_is_rounded_down_and_minimum_enforced(monkeypatch):
    broker=OkxDemoBroker("key","secret","pass")
    async def rules(_):return {"lot_size":__import__("decimal").Decimal("0.001"),"min_size":__import__("decimal").Decimal("0.01"),"tick_size":__import__("decimal").Decimal("0.1")}
    monkeypatch.setattr(broker,"instrument_rules",rules)
    assert asyncio.run(broker.normalize_size("BTC-USDT",0.0129))=="0.012"
    import pytest
    with pytest.raises(RuntimeError,match="BELOW_MINIMUM"):asyncio.run(broker.normalize_size("BTC-USDT",0.009))
    assert asyncio.run(broker.normalize_price("BTC-USDT",101.29))=="101.2"


def test_client_order_id_is_deterministic():
    first=BotService._client_id("bot","2026-01-01T00:00:00Z","buy")
    assert first==BotService._client_id("bot","2026-01-01T00:00:00Z","buy")
    assert len(first)<=32 and first.isalnum()
