import asyncio,pytest
from terminal.brokers import live_broker
from terminal.models import PaperOrderIn
def test_live_broker_is_fail_closed():
 assert not live_broker.capabilities.live_money
 with pytest.raises(PermissionError):asyncio.run(live_broker.submit("u",PaperOrderIn(instrument_id="x",side="buy",quantity=1),None))
