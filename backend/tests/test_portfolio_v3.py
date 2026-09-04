from datetime import datetime,timezone
from terminal.models import Freshness,PortfolioTransactionIn,Quote
from terminal.portfolio_v3 import PortfolioEngine
def tx(i,side,qty,price,currency):return PortfolioTransactionIn(instrument_id=i,side=side,quantity=qty,price=price,currency=currency,executed_at=datetime.now(timezone.utc))
def test_multicurrency_portfolio_converts_and_marks_complete():
 engine=PortfolioEngine();engine.add("u",tx("stock:xnas:aapl","buy",2,100,"USD"));engine.add("u",tx("stock:xist:thyao","buy",10,20,"TRY"))
 quotes={"stock:xnas:aapl":Quote(instrument_id="stock:xnas:aapl",price=110,source="t",freshness=Freshness.delayed,as_of=datetime.now(timezone.utc)),"stock:xist:thyao":Quote(instrument_id="stock:xist:thyao",price=25,source="t",freshness=Freshness.delayed,as_of=datetime.now(timezone.utc))}
 result=engine.summary("u",quotes,{"USD":1,"TRY":.03})
 assert result["total_value"]==227.5 and result["complete"]
def test_missing_fx_is_not_counted_as_zero():
 engine=PortfolioEngine();engine.add("u",tx("stock:xist:thyao","buy",10,20,"TRY"));result=engine.summary("u",{}, {},"USD")
 assert not result["complete"] and result["unpriced_instruments"]==["stock:xist:thyao"]
