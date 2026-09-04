from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, model_validator

def utcnow() -> datetime: return datetime.now(timezone.utc)

class AssetClass(str, Enum):
    crypto="crypto"; stock="stock"; etf="etf"; index="index"; fx="fx"; commodity="commodity"
class Freshness(str, Enum):
    live="live"; delayed="delayed"; stale="stale"; unavailable="unavailable"
class Instrument(BaseModel):
    id:str; symbol:str; display_symbol:str; name:str; asset_class:AssetClass; exchange:str
    mic:str|None=None; country:str|None=None; currency:str; quote_currency:str|None=None
    provider_symbols:dict[str,str]=Field(default_factory=dict); timezone:str="UTC"; trading_calendar:str="24/7"
    tick_size:float=.01; lot_size:float=1; price_precision:int=2; isin:str|None=None; figi:str|None=None
    active:bool=True; data_capabilities:list[str]=Field(default_factory=list)
class Quote(BaseModel):
    instrument_id:str; price:float|None=None; bid:float|None=None; ask:float|None=None; change:float|None=None
    change_pct:float|None=None; volume:float|None=None; source:str; freshness:Freshness; as_of:datetime; market_status:str="unknown"
class Candle(BaseModel):
    instrument_id:str; timeframe:str; open_time:datetime; open:float; high:float; low:float; close:float; volume:float
    source:str; freshness:Freshness; adjusted:bool=False; quality_flags:list[str]=Field(default_factory=list)
class Fundamentals(BaseModel):
    instrument_id:str; source:str; freshness:Freshness; as_of:datetime; currency:str|None=None
    market_cap:float|None=None; enterprise_value:float|None=None; trailing_pe:float|None=None; forward_pe:float|None=None
    price_to_book:float|None=None; enterprise_to_ebitda:float|None=None; dividend_yield:float|None=None
    revenue_growth:float|None=None; profit_margin:float|None=None; return_on_equity:float|None=None
    total_revenue:float|None=None; free_cash_flow:float|None=None; total_debt:float|None=None; total_cash:float|None=None
    circulating_supply:float|None=None; total_supply:float|None=None; fully_diluted_valuation:float|None=None
    fifty_two_week_high:float|None=None; fifty_two_week_low:float|None=None; sector:str|None=None; industry:str|None=None
    documents:list[dict[str,str]]=Field(default_factory=list)
class StatementPeriod(BaseModel):
    period:str; frequency:Literal["quarterly","annual"]; currency:str; income:dict[str,float|None]=Field(default_factory=dict)
    balance:dict[str,float|None]=Field(default_factory=dict); cashflow:dict[str,float|None]=Field(default_factory=dict); source:str; as_of:datetime
class CorporateAction(BaseModel):
    instrument_id:str; action_type:Literal["dividend","split","filing","earnings"]; event_date:datetime; value:float|None=None
    currency:str|None=None; title:str; source:str; url:str|None=None
class NewsItem(BaseModel):
    id:str; instrument_id:str|None=None; title:str; source:str; published_at:datetime|None=None; url:str; language:str="tr"
class PortfolioTransactionIn(BaseModel):
    instrument_id:str; side:Literal["buy","sell","dividend","deposit","withdrawal"]; quantity:float=Field(gt=0)
    price:float=Field(ge=0); fees:float=Field(default=0,ge=0); currency:str; executed_at:datetime=Field(default_factory=utcnow)
class SavedScreenIn(BaseModel):
    name:str=Field(min_length=1,max_length=80); filters:dict[str,Any]=Field(default_factory=dict); sort:str="change_pct"; direction:Literal["asc","desc"]="desc"
class SavedScreen(SavedScreenIn):
    id:UUID=Field(default_factory=uuid4); user_id:str; created_at:datetime=Field(default_factory=utcnow); updated_at:datetime=Field(default_factory=utcnow)
class PaperOrderIn(BaseModel):
    instrument_id:str; side:Literal["buy","sell"]; order_type:Literal["market","limit","stop","stop_limit","bracket","oco"]="market"
    quantity:float=Field(gt=0); limit_price:float|None=Field(default=None,gt=0); stop_price:float|None=Field(default=None,gt=0)
    take_profit:float|None=Field(default=None,gt=0); stop_loss:float|None=Field(default=None,gt=0)
    @model_validator(mode="after")
    def prices(self):
        if self.order_type in {"limit","stop_limit"} and self.limit_price is None: raise ValueError("limit_price is required")
        if self.order_type in {"stop","stop_limit"} and self.stop_price is None: raise ValueError("stop_price is required")
        if self.order_type in {"bracket","oco"} and (self.take_profit is None or self.stop_loss is None): raise ValueError("take_profit and stop_loss are required")
        return self
class AlertIn(BaseModel):
    instrument_id:str; field:Literal["price","change_pct","volume","rsi","relative_volume","trend_score","volatility"]; operator:Literal["above","below"]; target:float
    cooldown_seconds:int=Field(default=300,ge=0,le=86400)
class Alert(BaseModel):
    id:UUID=Field(default_factory=uuid4); user_id:str; instrument_id:str; field:str; operator:str; target:float
    cooldown_seconds:int=300; state:Literal["armed","triggered","paused"]="armed"; last_value:float|None=None
    last_triggered_at:datetime|None=None; created_at:datetime=Field(default_factory=utcnow)
class JournalEntryIn(BaseModel):
    instrument_id:str; order_id:UUID|None=None; title:str=Field(min_length=1,max_length=120); thesis:str=Field(default="",max_length=4000)
    strategy:str|None=Field(default=None,max_length=80); tags:list[str]=Field(default_factory=list,max_length=12); planned_risk:float|None=Field(default=None,ge=0)
    planned_reward:float|None=Field(default=None,ge=0); realized_r:float|None=None; mae:float|None=None; mfe:float|None=None
    rule_violations:list[str]=Field(default_factory=list,max_length=20); before_image_url:str|None=None; after_image_url:str|None=None
class JournalEntry(JournalEntryIn):
    id:UUID=Field(default_factory=uuid4); user_id:str; created_at:datetime=Field(default_factory=utcnow); updated_at:datetime=Field(default_factory=utcnow)
class PaperOrder(BaseModel):
    id:UUID=Field(default_factory=uuid4); user_id:str; account_id:str; instrument_id:str; side:Literal["buy","sell"]
    order_type:str; quantity:float; status:Literal["new","accepted","partially_filled","filled","cancelled","rejected"]
    limit_price:float|None=None; stop_price:float|None=None; fill_price:float|None=None; filled_quantity:float=0
    commission:float=0; realized_pnl:float|None=None; parent_id:UUID|None=None; oco_group:UUID|None=None; rejection_reason:str|None=None; created_at:datetime=Field(default_factory=utcnow); updated_at:datetime=Field(default_factory=utcnow)
    mae:float|None=None; mfe:float|None=None
class WorkspaceIn(BaseModel):
    name:str=Field(min_length=1,max_length=80); layout:dict[str,Any]; is_default:bool=False
class Workspace(WorkspaceIn):
    id:UUID=Field(default_factory=uuid4); user_id:str; updated_at:datetime=Field(default_factory=utcnow)
class Position(BaseModel):
    instrument_id:str; quantity:float; average_price:float; last_price:float|None; market_value:float|None
    unrealized_pnl:float|None; currency:str; freshness:Freshness
class ApiMeta(BaseModel):
    as_of:datetime=Field(default_factory=utcnow); source:str; freshness:Freshness; currency:str|None=None; market_status:str|None=None; next_cursor:str|None=None
class ApiResponse(BaseModel): data:Any; meta:ApiMeta
