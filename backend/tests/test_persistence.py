import asyncio
from terminal.persistence import Repository
def test_memory_repository_is_noop_but_contract_compatible(monkeypatch):
 monkeypatch.setenv("PERSISTENCE","memory");repo=Repository()
 row={"id":"1","user_id":"u"}
 assert asyncio.run(repo.upsert("paper_orders",row))==row
 assert asyncio.run(repo.list("paper_orders","u")) is None
 assert asyncio.run(repo.health())["status"]=="memory"
