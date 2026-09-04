from terminal.journal_analytics import summarize_orders
def test_journal_metrics_include_costs_and_expectancy():
 rows=[{"status":"filled","side":"buy","instrument_id":"x","commission":1},{"status":"filled","side":"sell","instrument_id":"x","commission":1,"realized_pnl":10},{"status":"filled","side":"sell","instrument_id":"x","commission":1,"realized_pnl":-5}];x=summarize_orders(rows);assert x["win_rate_pct"]==50 and x["expectancy"]==2.5 and x["commissions"]==3
