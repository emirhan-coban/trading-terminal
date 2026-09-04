"""Global multi-asset research and paper-trading API."""
import os
from uuid import uuid4
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from terminal.api import router
app=FastAPI(title="Global Trading Terminal API",version="3.0.0",description="Multi-asset research and paper trading API")
app.add_middleware(CORSMiddleware,allow_origins=os.getenv("CORS_ORIGINS","http://localhost:3000").split(","),allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
@app.middleware("http")
async def correlation_id(request:Request,call_next):
 cid=request.headers.get("x-correlation-id",str(uuid4())); response=await call_next(request); response.headers["x-correlation-id"]=cid; return response
@app.get("/health")
async def health():return {"status":"ok","version":"3.0.0"}
app.include_router(router)
