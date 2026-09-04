from __future__ import annotations
import asyncio,os
from dataclasses import dataclass
from fastapi import HTTPException
from supabase import create_client

@dataclass(frozen=True)
class UserContext:user_id:str;mode:str

async def authenticate(authorization:str|None)->UserContext:
 require=os.getenv("REQUIRE_AUTH","false").lower()=="true"
 if not authorization:
  if require:raise HTTPException(401,detail={"code":"AUTH_REQUIRED","message":"Oturum açmanız gerekiyor"})
  return UserContext("local-user","local")
 scheme,_,token=authorization.partition(" ")
 if scheme.lower()!="bearer" or not token:raise HTTPException(401,detail={"code":"INVALID_AUTH","message":"Geçersiz erişim belirteci"})
 url=os.getenv("SUPABASE_URL","");key=os.getenv("SUPABASE_KEY","")
 if not url or not key:
  if require:raise HTTPException(503,detail={"code":"AUTH_UNAVAILABLE","message":"Kimlik servisi yapılandırılmamış"})
  return UserContext("local-user","local")
 try:
  client=create_client(url,key);result=await asyncio.to_thread(client.auth.get_user,token)
  if not result.user:raise ValueError("missing user")
  return UserContext(str(result.user.id),"supabase")
 except Exception as e:raise HTTPException(401,detail={"code":"INVALID_AUTH","message":"Oturum doğrulanamadı"}) from e
