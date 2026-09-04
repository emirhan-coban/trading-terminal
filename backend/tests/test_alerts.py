from datetime import datetime,timezone
from terminal.alerts import AlertEngine
from terminal.models import AlertIn,Freshness,Quote
def q(price):return Quote(instrument_id="crypto:binance:btcusdt",price=price,source="test",freshness=Freshness.live,as_of=datetime.now(timezone.utc))
def test_alert_is_edge_triggered_and_rearms():
 engine=AlertEngine();engine.create("u",AlertIn(instrument_id="crypto:binance:btcusdt",field="price",operator="above",target=100))
 assert len(engine.evaluate("u",q(101)))==1
 assert engine.evaluate("u",q(102))==[]
 assert engine.evaluate("u",q(99))==[]
 assert len(engine.evaluate("u",q(103)))==1
