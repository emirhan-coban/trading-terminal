import asyncio,hashlib,urllib.parse,urllib.request,xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from .models import NewsItem
def _rss(query,instrument_id,limit):
 url="https://news.google.com/rss/search?q="+urllib.parse.quote(query)+"&hl=tr&gl=TR&ceid=TR:tr";req=urllib.request.Request(url,headers={"User-Agent":"GlobalTerminal/1.0"})
 with urllib.request.urlopen(req,timeout=10) as response:root=ET.fromstring(response.read())
 out=[]
 for node in list(root.iter("item"))[:limit]:
  title=(node.findtext("title") or "").strip();link=(node.findtext("link") or "").strip();source=node.find("source");published=node.findtext("pubDate")
  try:dt=parsedate_to_datetime(published) if published else None
  except (TypeError,ValueError):dt=None
  out.append(NewsItem(id=hashlib.sha1(link.encode()).hexdigest(),instrument_id=instrument_id,title=title,source=source.text.strip() if source is not None and source.text else "Google News",published_at=dt,url=link))
 return out
async def news_for(instrument,limit=12):return await asyncio.to_thread(_rss,f'"{instrument.name}" OR {instrument.symbol}',instrument.id,limit)
