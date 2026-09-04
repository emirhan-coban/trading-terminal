from datetime import datetime,timezone
from terminal.models import CorporateAction,StatementPeriod
def test_statement_keeps_actual_missing_fields():
 row=StatementPeriod(period="2025-12-31",frequency="annual",currency="USD",income={"revenue":10,"net_income":None},source="test",as_of=datetime.now(timezone.utc))
 assert row.income["net_income"] is None
def test_corporate_action_is_typed():
 row=CorporateAction(instrument_id="stock:xnas:aapl",action_type="dividend",event_date=datetime.now(timezone.utc),value=.25,title="Dividend",source="test")
 assert row.action_type=="dividend"
