from datetime import datetime, timezone

from terminal.models import Freshness, PaperOrderIn, Quote
from terminal.paper import PaperBroker


def quote(price: float):
    return Quote(instrument_id="crypto:binance:btcusdt", price=price, source="test",
                 freshness=Freshness.live, as_of=datetime.now(timezone.utc))


def test_bracket_creates_oco_children_and_cancels_sibling():
    broker = PaperBroker()
    parent = broker.submit("u", PaperOrderIn(instrument_id="crypto:binance:btcusdt", side="buy",
                           order_type="bracket", quantity=1, take_profit=110, stop_loss=90), quote(100))
    assert parent.status == "filled"
    assert len(broker.fills["u"]) == 1
    assert broker.cash_ledger["u"][0]["amount"] < 0
    children = [x for x in broker.orders["u"] if x.parent_id == parent.id]
    assert {x.order_type for x in children} == {"limit", "stop"}
    changed = broker.process("u", quote(111))
    assert {x.status for x in changed} == {"filled", "cancelled"}
    assert broker.holdings["u"] == {}


def test_resting_order_partial_fill():
    broker = PaperBroker()
    broker.submit("u", PaperOrderIn(instrument_id="crypto:binance:btcusdt", side="buy",
                  order_type="market", quantity=2), quote(100))
    order = broker.submit("u", PaperOrderIn(instrument_id="crypto:binance:btcusdt", side="sell",
                         order_type="limit", quantity=2, limit_price=110), quote(100))
    broker.process("u", quote(111), available_quantity=.5)
    assert order.status == "partially_filled"
    assert order.filled_quantity == .5
    broker.process("u", quote(112))
    assert order.status == "filled"
    assert order.filled_quantity == 2
    assert len(broker.fills["u"]) == 3

def test_mae_mfe_are_computed_from_live_quotes():
    broker=PaperBroker();broker.submit("u",PaperOrderIn(instrument_id="crypto:binance:btcusdt",side="buy",quantity=1),quote(100))
    broker.process("u",quote(95));broker.process("u",quote(110))
    closed=broker.submit("u",PaperOrderIn(instrument_id="crypto:binance:btcusdt",side="sell",quantity=1),quote(108))
    assert closed.mae < -5
    assert closed.mfe > 9
