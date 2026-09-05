"""End-to-end integration test for the task-11 literature search & credits APIs.

Runs against a throwaway SQLite database (via DATABASE_URL override) so it can
execute without a live PostgreSQL server.

Run from backend/:
    python -m pytest tests/test_literature_credits_e2e.py -q
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./_test_e2e.db")
os.environ.setdefault("LITERATURE_MODE", "mock")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import models  # noqa: E402
from database import Base, AsyncSessionLocal, engine  # noqa: E402
from main import app  # noqa: E402
from models.credit import CreditTransaction  # noqa: E402
from models.project import Project  # noqa: E402
from models.user import User  # noqa: E402
from security import create_access_token  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def prepare_db():
    if os.path.exists("_test_e2e.db"):
        os.remove("_test_e2e.db")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client):
    async def _seed():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with AsyncSessionLocal() as db:
            user = User(email="test@example.com", display_name="Tester", credit_balance=10)
            db.add(user)
            await db.flush()
            project = Project(user_id=user.id, title="Thesis", topic="AI", status="draft")
            db.add(project)
            await db.commit()
            await db.refresh(user)
            await db.refresh(project)
            return user, project

    import asyncio
    user, project = asyncio.run(_seed())
    token = create_access_token(str(user.id))
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "project_id": str(project.id),
        "user": user,
    }


def _search(client, auth, query, filters=None):
    url = f"/api/v1/projects/{auth['project_id']}/literature/search"
    return client.post(url, headers=auth["headers"], json={
        "query": query,
        "filters": filters,
    })


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_credits_balance(client, auth):
    r = client.get("/api/v1/credits/balance", headers=auth["headers"])
    assert r.status_code == 200
    assert r.json()["balance"] == 10


def test_search_deducts_credit_and_caches(client, auth):
    # Fresh search: 3 papers, deducts 1 credit.
    r = _search(client, auth, "academic writing")
    assert r.status_code == 200
    fresh = r.json()
    assert fresh["cached"] is False
    assert len(fresh["papers"]) == 3
    assert fresh["papers"][0]["summary"]

    r = client.get("/api/v1/credits/balance", headers=auth["headers"])
    assert r.json()["balance"] == 9

    # Same query again: served from cache, no credit change.
    r = _search(client, auth, "academic writing")
    assert r.status_code == 200
    cached = r.json()
    assert cached["cached"] is True
    assert cached["papers"][0]["id"] == fresh["papers"][0]["id"]

    r = client.get("/api/v1/credits/balance", headers=auth["headers"])
    assert r.json()["balance"] == 9


def test_search_filters(client, auth):
    r = _search(client, auth, "arxiv only", {"source": "arxiv"})
    assert r.status_code == 200
    body = r.json()
    assert body["cached"] is False
    assert all(p["source"] == "arxiv" for p in body["papers"])


def test_search_foreign_project_404(client, auth):
    import uuid
    url = f"/api/v1/projects/{uuid.uuid4()}/literature/search"
    r = client.post(url, headers=auth["headers"], json={"query": "x"})
    assert r.status_code == 404


def test_search_unauthenticated_401(client, auth):
    url = f"/api/v1/projects/{auth['project_id']}/literature/search"
    r = client.post(url, json={"query": "x"})
    assert r.status_code == 401


def test_search_insufficient_credits_402(client, auth):
    async def _drain():
        async with AsyncSessionLocal() as db:
            user = await db.get(User, auth["user"].id)
            user.credit_balance = 0
            db.add(CreditTransaction(user_id=user.id, amount=-10,
                                     balance_after=0, transaction_type="usage"))
            await db.commit()
    import asyncio
    asyncio.run(_drain())

    r = _search(client, auth, "no budget")
    assert r.status_code == 402