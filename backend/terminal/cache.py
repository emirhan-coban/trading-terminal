from __future__ import annotations
import json,os
from datetime import datetime,timezone
from typing import Any
try:
 import redis.asyncio as redis
except ImportError:redis=None

class QuoteCache:
 def __init__(self):self.url=os.getenv("REDIS_URL","");self.client=redis.from_url(self.url,decode_responses=True) if redis and self.url else None;self.memory={}
 async def set(self,key:str,value:dict,ttl=60):
  payload=json.dumps(value,default=str);self.memory[key]=(payload,datetime.now(timezone.utc))
  if self.client:
   try:await self.client.set(f"terminal:quote:{key}",payload,ex=ttl)
   except Exception:pass
 async def get(self,key:str)->dict|None:
  if self.client:
   try:
    raw=await self.client.get(f"terminal:quote:{key}")
    if raw:return json.loads(raw)
   except Exception:pass
  row=self.memory.get(key);return json.loads(row[0]) if row else None
 async def health(self)->dict[str,Any]:
  if not self.client:return {"provider":"redis","status":"memory-fallback"}
  try:await self.client.ping();return {"provider":"redis","status":"ok"}
  except Exception as e:return {"provider":"redis","status":"error","detail":type(e).__name__}
quote_cache=QuoteCache()
