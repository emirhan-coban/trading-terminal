from __future__ import annotations
import asyncio,os
from typing import Any
from supabase import create_client

class Repository:
 """Async persistence boundary. Disabled by default for dependency-free local mode."""
 def __init__(self):
  self.enabled=os.getenv("PERSISTENCE","memory").lower()=="supabase"
  self.client=None
  if self.enabled:
   url=os.getenv("SUPABASE_URL","");key=os.getenv("SUPABASE_KEY","")
   if not url or not key:raise RuntimeError("Supabase persistence requires SUPABASE_URL and SUPABASE_KEY")
   self.client=create_client(url,key)
 async def upsert(self,table:str,row:dict[str,Any],conflict="id"):
  if not self.client:return row
  payload={k:v for k,v in row.items() if v is not None}
  return await asyncio.to_thread(lambda:(self.client.table(table).upsert(payload,on_conflict=conflict).execute().data or [payload])[0])
 async def list(self,table:str,user_id:str,order="created_at",desc=True):
  if not self.client:return None
  return await asyncio.to_thread(lambda:self.client.table(table).select("*").eq("user_id",user_id).order(order,desc=desc).execute().data or [])
 async def delete(self,table:str,user_id:str,row_id:str):
  if not self.client:return True
  await asyncio.to_thread(lambda:self.client.table(table).delete().eq("user_id",user_id).eq("id",row_id).execute());return True
 async def replace_positions(self,user_id:str,account_id:str,rows:list[dict]):
  if not self.client:return
  def write():
   self.client.table("paper_positions").delete().eq("user_id",user_id).eq("account_id",account_id).execute()
   if rows:self.client.table("paper_positions").insert(rows).execute()
  await asyncio.to_thread(write)
 async def sync_position(self,user_id:str,account_id:str,instrument_id:str,position:dict|None):
  if not self.client:return
  if position:
   row={"user_id":user_id,"account_id":account_id,"instrument_id":instrument_id,"quantity":position["quantity"],"average_price":position["average_price"]}
   await self.upsert("paper_positions",row,"account_id,instrument_id")
  else:await asyncio.to_thread(lambda:self.client.table("paper_positions").delete().eq("user_id",user_id).eq("account_id",account_id).eq("instrument_id",instrument_id).execute())
 async def health(self):
  if not self.client:return {"provider":"persistence","status":"memory"}
  try:await asyncio.to_thread(lambda:self.client.table("instruments").select("id",count="exact").limit(1).execute());return {"provider":"persistence","status":"ok"}
  except Exception as e:return {"provider":"persistence","status":"error","detail":type(e).__name__}
repository=Repository()
