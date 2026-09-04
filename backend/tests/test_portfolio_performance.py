from datetime import datetime,timezone,timedelta
from terminal.portfolio_performance import performance,stress,time_weighted_return,xirr

def test_xirr_and_performance_metadata():
 now=datetime.now(timezone.utc)
 rate=xirr([(now-timedelta(days=365),-100),(now,110)])
 assert 9.9<rate<10.1
 result=performance([{"side":"buy","quantity":1,"price":100,"fees":0,"executed_at":now-timedelta(days=365)}],110)
 assert 9.9<result["money_weighted_return_pct"]<10.1
 assert result["twr_status"]=="requires_position_snapshots"

def test_stress_keeps_assumptions_visible():
 result=stress([{"instrument_id":"x","asset_class":"stock","base_value":100}],{"stock":-.2})
 assert result["total_impact"]==-20
 assert result["positions"][0]["shock_pct"]==-20

def test_time_weighted_return_removes_external_flow():
 rows=[{"as_of":"2025-01-01","total_value":100},{"as_of":"2025-02-01","total_value":165,"external_flow":50},{"as_of":"2025-03-01","total_value":181.5,"external_flow":0}]
 assert time_weighted_return(rows)==21
