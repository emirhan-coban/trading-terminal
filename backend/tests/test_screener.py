from datetime import datetime,timezone
from terminal.models import Freshness,Quote
from terminal.screener import screen
def quote(i,p,c):return Quote(instrument_id=i,price=p,change_pct=c,source="test",freshness=Freshness.live,as_of=datetime.now(timezone.utc))
def test_screen_filters_asset_and_change():
 rows=screen([quote("crypto:binance:btcusdt",100,4),quote("stock:xnas:aapl",200,-1)],asset_class="crypto",min_change_pct=2)
 assert len(rows)==1 and rows[0]["instrument"]["display_symbol"]=="BTC/USDT"
