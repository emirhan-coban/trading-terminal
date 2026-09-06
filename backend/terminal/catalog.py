import json
from pathlib import Path
from .models import AssetClass, Instrument

CORE=[
 Instrument(id="crypto:okx:btc-usdt",symbol="BTC-USDT",display_symbol="BTC/USDT",name="Bitcoin",asset_class=AssetClass.crypto,exchange="OKX",currency="BTC",quote_currency="USDT",provider_symbols={"okx":"BTC-USDT","coingecko":"bitcoin"},lot_size=.00000001,data_capabilities=["quote","candles"]),
 Instrument(id="crypto:okx:eth-usdt",symbol="ETH-USDT",display_symbol="ETH/USDT",name="Ethereum",asset_class=AssetClass.crypto,exchange="OKX",currency="ETH",quote_currency="USDT",provider_symbols={"okx":"ETH-USDT","coingecko":"ethereum"},lot_size=.000001,data_capabilities=["quote","candles"]),
 Instrument(id="crypto:binance:btcusdt",symbol="BTCUSDT",display_symbol="BTC/USDT",name="Bitcoin",asset_class=AssetClass.crypto,exchange="BINANCE",currency="BTC",quote_currency="USDT",provider_symbols={"binance":"BTCUSDT","coingecko":"bitcoin"},lot_size=.00001,data_capabilities=["quote","candles","trades","depth"]),
 Instrument(id="crypto:binance:ethusdt",symbol="ETHUSDT",display_symbol="ETH/USDT",name="Ethereum",asset_class=AssetClass.crypto,exchange="BINANCE",currency="ETH",quote_currency="USDT",provider_symbols={"binance":"ETHUSDT","coingecko":"ethereum"},lot_size=.0001,data_capabilities=["quote","candles","trades","depth"]),
 Instrument(id="stock:xnas:aapl",symbol="AAPL",display_symbol="AAPL",name="Apple Inc.",asset_class=AssetClass.stock,exchange="NASDAQ",mic="XNAS",country="US",currency="USD",provider_symbols={"yfinance":"AAPL","sec_cik":"0000320193"},timezone="America/New_York",trading_calendar="XNYS",data_capabilities=["quote","candles","fundamentals","filings"]),
 Instrument(id="stock:xist:thyao",symbol="THYAO",display_symbol="THYAO",name="Türk Hava Yolları",asset_class=AssetClass.stock,exchange="BIST",mic="XIST",country="TR",currency="TRY",provider_symbols={"yfinance":"THYAO.IS","kap":"THYAO"},timezone="Europe/Istanbul",trading_calendar="XIST",data_capabilities=["quote","candles","fundamentals"]),
 Instrument(id="index:index:spx",symbol="SPX",display_symbol="S&P 500",name="S&P 500 Index",asset_class=AssetClass.index,exchange="INDEX",country="US",currency="USD",provider_symbols={"yfinance":"^GSPC"},timezone="America/New_York",trading_calendar="XNYS",data_capabilities=["quote","candles"]),]
CORE.extend([
 Instrument(id="etf:xnas:qqq",symbol="QQQ",display_symbol="QQQ",name="Invesco QQQ Trust",asset_class=AssetClass.etf,exchange="NASDAQ",mic="XNAS",country="US",currency="USD",provider_symbols={"yfinance":"QQQ"},timezone="America/New_York",trading_calendar="XNYS",data_capabilities=["quote","candles","fundamentals"]),
 Instrument(id="fx:otc:eurusd",symbol="EURUSD",display_symbol="EUR/USD",name="Euro / US Dollar",asset_class=AssetClass.fx,exchange="OTC",currency="EUR",quote_currency="USD",provider_symbols={"yfinance":"EURUSD=X"},timezone="UTC",trading_calendar="24/5",tick_size=.00001,price_precision=5,data_capabilities=["quote","candles"]),
 Instrument(id="commodity:comex:gold",symbol="GC",display_symbol="GOLD",name="Gold Futures",asset_class=AssetClass.commodity,exchange="COMEX",country="US",currency="USD",provider_symbols={"yfinance":"GC=F"},timezone="America/New_York",trading_calendar="CME",tick_size=.1,price_precision=2,data_capabilities=["quote","candles"]),
])
class InstrumentCatalog:
 def __init__(self):
  self.items={x.id:x for x in CORE}; path=Path(__file__).parents[1]/"bist_symbols.json"
  if path.exists():
   for row in json.loads(path.read_text(encoding="utf-8")):
    symbol=str(row["ticker"]).upper(); item=Instrument(id=f"stock:xist:{symbol.lower()}",symbol=symbol,display_symbol=symbol,name=row["name"],asset_class=AssetClass.stock,exchange="BIST",mic="XIST",country="TR",currency="TRY",provider_symbols={"yfinance":f"{symbol}.IS","kap":symbol},timezone="Europe/Istanbul",trading_calendar="XIST",data_capabilities=["quote","candles","fundamentals"]); self.items.setdefault(item.id,item)
 def get(self,id): return self.items.get(id)
 def search(self,q,asset_class=None,limit=20):
  q=q.casefold().strip(); rows=[]
  for x in self.items.values():
   if asset_class and x.asset_class.value!=asset_class: continue
   if q not in f"{x.symbol} {x.display_symbol} {x.name} {x.exchange}".casefold(): continue
   rank=0 if x.symbol.casefold()==q else 1 if x.symbol.casefold().startswith(q) else 2; rows.append((rank,x.symbol,x))
  return [x for _,__,x in sorted(rows)[:limit]]
catalog=InstrumentCatalog()
