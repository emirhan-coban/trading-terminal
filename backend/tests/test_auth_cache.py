import asyncio
import pytest
from fastapi import HTTPException
from terminal.auth import authenticate
from terminal.cache import QuoteCache

def test_local_auth_is_explicit_fallback(monkeypatch):
 monkeypatch.setenv("REQUIRE_AUTH","false")
 assert asyncio.run(authenticate(None)).mode=="local"

def test_required_auth_rejects_anonymous(monkeypatch):
 monkeypatch.setenv("REQUIRE_AUTH","true")
 with pytest.raises(HTTPException) as error:asyncio.run(authenticate(None))
 assert error.value.status_code==401

def test_memory_cache_survives_without_redis(monkeypatch):
 monkeypatch.delenv("REDIS_URL",raising=False);cache=QuoteCache();asyncio.run(cache.set("x",{"price":10}));assert asyncio.run(cache.get("x"))["price"]==10
