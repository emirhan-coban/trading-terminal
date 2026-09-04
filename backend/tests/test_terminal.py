from datetime import datetime,timezone
from terminal.catalog import catalog
from terminal.models import Freshness,PaperOrderIn,Quote
from terminal.paper import PaperBroker
def quote(price=100,freshness=Freshness.live):return Quote(instrument_id="crypto:binance:btcusdt",price=price,source="test",freshness=freshness,as_of=datetime.now(timezone.utc))
def test_global_catalog_resolves_three_markets():
 assert catalog.get("crypto:binance:btcusdt").display_symbol=="BTC/USDT"
 assert catalog.get("stock:xnas:aapl").currency=="USD"
 assert catalog.get("stock:xist:thyao").mic=="XIST"
 assert catalog.get("etf:xnas:qqq").asset_class.value=="etf"
 assert catalog.get("fx:otc:eurusd").price_precision==5
 assert catalog.get("commodity:comex:gold").exchange=="COMEX"
def test_search_does_not_append_bist_suffix(): assert catalog.search("AAPL")[0].id=="stock:xnas:aapl"
def test_market_order_fills_with_costs():
 broker=PaperBroker(); order=broker.submit("u",PaperOrderIn(instrument_id="crypto:binance:btcusdt",side="buy",quantity=1),quote())
 assert order.status=="filled" and order.fill_price>100 and order.commission>0
def test_stale_order_is_rejected():
 broker=PaperBroker(); order=broker.submit("u",PaperOrderIn(instrument_id="crypto:binance:btcusdt",side="buy",quantity=1),quote(freshness=Freshness.stale))
 assert order.status=="rejected" and order.rejection_reason=="STALE_MARKET_DATA"
def test_oversell_is_rejected():
 broker=PaperBroker(); order=broker.submit("u",PaperOrderIn(instrument_id="crypto:binance:btcusdt",side="sell",quantity=1),quote())
 assert order.status=="rejected" and order.rejection_reason=="INSUFFICIENT_POSITION"
