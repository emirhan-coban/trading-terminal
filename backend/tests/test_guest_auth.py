import asyncio
import pytest
from fastapi import HTTPException
from terminal.auth import authenticate


def run(coro):
    return asyncio.run(coro)


def test_guest_gets_isolated_identity(monkeypatch):
    monkeypatch.setenv("ALLOW_GUEST", "true")
    a = run(authenticate("Guest abcd1234efgh"))
    b = run(authenticate("Guest zzzz9999yyyy"))
    assert a.mode == "guest" and a.user_id != b.user_id


def test_guest_disabled_falls_back_to_local(monkeypatch):
    monkeypatch.delenv("ALLOW_GUEST", raising=False)
    monkeypatch.delenv("REQUIRE_AUTH", raising=False)
    assert run(authenticate("Guest abcd1234efgh")).mode == "local"


def test_guest_rejected_when_auth_required_and_guests_off(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    monkeypatch.delenv("ALLOW_GUEST", raising=False)
    with pytest.raises(HTTPException) as e:
        run(authenticate("Guest abcd1234efgh"))
    assert e.value.status_code == 401


def test_guest_id_is_validated(monkeypatch):
    monkeypatch.setenv("ALLOW_GUEST", "true")
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    with pytest.raises(HTTPException):
        run(authenticate("Guest ../../etc"))
