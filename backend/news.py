"""Haber akışı — Google News RSS (anahtarsız), 15 dk bellek cache'i.

Not: yatırım tavsiyesi değil, bilgi amaçlı başlıklar.
"""

import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

_CACHE: dict = {}
TTL = 15 * 60


def _fetch_rss(query: str, limit: int = 8) -> list:
    now = time.time()
    if query in _CACHE and now - _CACHE[query][0] < TTL:
        return _CACHE[query][1][:limit]

    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(query) +
           "&hl=tr&gl=TR&ceid=TR:tr")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    items = []
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read())
        for node in root.iter("item")[:limit]:
            title = (node.findtext("title") or "").strip()
            link = (node.findtext("link") or "").strip()
            pub = (node.findtext("pubDate") or "").strip()
            source = node.find("source")
            items.append({
                "title": title,
                "link": link,
                "published": pub,
                "source": source.text.strip() if source is not None and source.text else "",
            })
    except Exception:
        items = []

    _CACHE[query] = (now, items)
    return items


def get_ticker_news(ticker_raw: str, limit: int = 8) -> dict:
    bare = ticker_raw.strip().upper().replace(".IS", "")
    items = _fetch_rss(f"{bare} hisse senedi borsa", limit=limit)
    return {"ticker": bare, "count": len(items), "items": items}


def get_market_news(limit: int = 10) -> dict:
    items = _fetch_rss("Borsa İstanbul BIST ekonomi", limit=limit)
    return {"count": len(items), "items": items}
