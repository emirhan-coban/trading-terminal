from terminal.alerts import AlertEngine
from terminal.models import AlertIn
def test_indicator_alert_is_edge_triggered():
 e=AlertEngine();e.create("u",AlertIn(instrument_id="x",field="rsi",operator="above",target=70));assert len(e.evaluate_snapshot("u","x",{"rsi":71}))==1;assert e.evaluate_snapshot("u","x",{"rsi":75})==[];e.evaluate_snapshot("u","x",{"rsi":60});assert len(e.evaluate_snapshot("u","x",{"rsi":72}))==1
