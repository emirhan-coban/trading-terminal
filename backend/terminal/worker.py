"""Background quote warmer. Run with: python -m terminal.worker"""
import asyncio,logging
from .cache import quote_cache
from .catalog import CORE
from .providers import providers
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
async def tick():
 for instrument in CORE:
  try:
   quote=await providers.for_instrument(instrument).quote(instrument);await quote_cache.set(instrument.id,quote.model_dump(mode="json"),ttl=90)
  except Exception as e:logging.warning("quote_warm_failed instrument=%s error=%s",instrument.id,type(e).__name__)
async def main():
 while True:await tick();await asyncio.sleep(15)
if __name__=="__main__":asyncio.run(main())
