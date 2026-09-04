import asyncio
from terminal.ai_research import summarize
from terminal.catalog import catalog
def test_ai_summary_has_deterministic_offline_fallback(monkeypatch):
 monkeypatch.delenv("GEMINI_API_KEY",raising=False);x=asyncio.run(summarize(catalog.get("stock:xnas:aapl"),{"trailing_pe":20},{"rsi":55,"trend_score":100,"momentum_20d":3}));assert not x["ai"] and "AL/SAT" in x["text"]
