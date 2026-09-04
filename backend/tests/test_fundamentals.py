from datetime import datetime,timezone
from terminal.models import Freshness,Fundamentals
def test_fundamentals_preserves_missing_data():
 row=Fundamentals(instrument_id="stock:xnas:aapl",source="test",freshness=Freshness.delayed,as_of=datetime.now(timezone.utc),currency="USD",market_cap=100)
 assert row.market_cap==100 and row.trailing_pe is None and row.documents==[]
def test_crypto_fundamentals_has_separate_supply_fields():
 row=Fundamentals(instrument_id="crypto:binance:btcusdt",source="test",freshness=Freshness.delayed,as_of=datetime.now(timezone.utc),circulating_supply=19,fully_diluted_valuation=21)
 assert row.circulating_supply==19 and row.total_revenue is None
