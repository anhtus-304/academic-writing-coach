"""Week-3 integration tests - literature search, 48h cache and selected papers.

Runs offline: ``LITERATURE_MODE=mock`` (conftest) feeds a deterministic corpus
and the LLM query-expansion call is stubbed out, so no network/OpenRouter access
happens. Cache behaviour (``cached`` flag + credit deduction) is verified against
the SQLite test database.
"""
import time

import pytest

from tests.conftest import create_user_with_project

SEARCH_URL = "/api/v1/projects/{project_id}/literature/search"


@pytest.fixture(autouse=True)
def offline_query_generation(monkeypatch):
    """Stub the LLM query generator so tests never call OpenRouter."""
    try:
        from backend.agents.literature_agent import literature_agent
    except ImportError:
        from agents.literature_agent import literature_agent

    async def _raise(*args, **kwargs):
        raise RuntimeError("offline test: LLM query generation disabled")

    monkeypatch.setattr(literature_agent, "generate_queries", _raise, raising=False)
    return literature_agent


async def _search(client, headers, project_id, query="academic writing", filters=None):
    return await client.post(
        SEARCH_URL.format(project_id=project_id),
        headers=headers,
        json={"query": query, "filters": filters},
    )


async def test_search_returns_papers_and_deducts_one_credit(client, project, auth_headers):
    balance_before = (await client.get("/api/v1/credits/balance", headers=auth_headers)).json()["balance"]

    res = await _search(client, auth_headers, project.id)
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["cached"] is False
    assert body["search_session_id"]
    assert body["total_results"] == len(body["papers"]) > 0
    assert body["expanded_queries"] == ["academic writing"]
    assert body["papers"][0]["summary"]

    balance_after = (await client.get("/api/v1/credits/balance", headers=auth_headers)).json()["balance"]
    assert balance_after == balance_before - 1


async def test_second_search_hits_cache_and_costs_nothing(client, project, auth_headers):
    first = await _search(client, auth_headers, project.id, query="citation agent")
    assert first.status_code == 200
    balance_after_first = (await client.get("/api/v1/credits/balance", headers=auth_headers)).json()["balance"]

    second = await _search(client, auth_headers, project.id, query="citation agent")
    assert second.status_code == 200
    cached_body = second.json()

    assert cached_body["cached"] is True
    assert cached_body["search_session_id"] == first.json()["search_session_id"]
    assert [p["id"] for p in cached_body["papers"]] == [p["id"] for p in first.json()["papers"]]

    balance_after_second = (await client.get("/api/v1/credits/balance", headers=auth_headers)).json()["balance"]
    assert balance_after_second == balance_after_first


async def test_expired_cache_forces_new_search(client, project, auth_headers, db_session):
    from datetime import datetime, timedelta, timezone

    from models.search_session import SearchSession

    created = await _search(client, auth_headers, project.id, query="expiring cache query")
    assert created.status_code == 200
    session_id = created.json()["search_session_id"]

    # Force the cached session to be expired (48h TTL reached).
    session = await db_session.get(SearchSession, session_id)
    session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    again = await _search(client, auth_headers, project.id, query="expiring cache query")
    assert again.status_code == 200
    assert again.json()["cached"] is False
    assert again.json()["search_session_id"] != session_id


async def test_search_source_filter(client, project, auth_headers):
    res = await _search(client, auth_headers, project.id, query="arxiv probe", filters={"source": "arxiv"})
    assert res.status_code == 200
    papers = res.json()["papers"]
    assert papers
    assert all(p["source"] == "arxiv" for p in papers)


async def test_search_without_credits_returns_402(client):
    from security import create_access_token

    user, project = await create_user_with_project(credit_balance=0)
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    res = await _search(client, headers, project.id, query="no credits")
    assert res.status_code == 402


async def test_search_requires_auth_and_valid_project(client, auth_headers, project):
    assert (await client.post(SEARCH_URL.format(project_id=project.id), json={"query": "x"})).status_code == 401

    import uuid

    foreign = await _search(client, auth_headers, uuid.uuid4(), query="x")
    assert foreign.status_code == 404


async def test_select_list_and_remove_paper(client, project, auth_headers):
    selected = await client.post(
        f"/api/v1/projects/{project.id}/literature/select",
        headers=auth_headers,
        json={
            "paper": {
                "title": "Transformer Models for Academic Writing",
                "authors": ["Nguyen Van An", "Le Thi B"],
                "year": 2023,
                "doi": "10.1109/w3.test.001",
                "url": "https://example.org/w3-test",
                "abstract": "A study about writing assistants.",
            },
            "notes": "Chapter 2 evidence",
        },
    )
    assert selected.status_code == 200, selected.text
    selected_id = selected.json()["id"]
    assert "Nguyen" in (selected.json()["citation_formatted"] or "")

    listed = await client.get(f"/api/v1/projects/{project.id}/literature/selected", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["selected_papers"][0]["id"] == selected_id

    removed = await client.delete(
        f"/api/v1/projects/{project.id}/literature/selected/{selected_id}",
        headers=auth_headers,
    )
    assert removed.status_code == 200

    empty = await client.get(f"/api/v1/projects/{project.id}/literature/selected", headers=auth_headers)
    assert empty.json()["total"] == 0


async def test_recent_search_endpoint(client, project, auth_headers):
    await _search(client, auth_headers, project.id, query="recent search probe")

    res = await client.get(f"/api/v1/projects/{project.id}/literature/recent-search", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["has_recent"] is True
    assert body["query"] == "recent search probe"
    assert body["papers"]


async def test_full_text_search_helper_uses_portable_fallback(db_session):
    """``full_text_search_papers`` must work on SQLite (ILIKE) and PostgreSQL (GIN)."""
    from services import literature_service
    from tests.conftest import create_cached_paper

    await create_cached_paper(
        db_session,
        title="Graph Neural Networks in Education",
        abstract="A survey of graph learning applied to learning analytics.",
        relevance_score=0.9,
    )

    started = time.perf_counter()
    hits = await literature_service.full_text_search_papers(db_session, "Graph Neural", limit=5)
    elapsed = time.perf_counter() - started

    assert any("Graph Neural Networks" in paper.title for paper in hits)
    # Smoke-check for query performance regressions (generous bound for SQLite).
    assert elapsed < 0.5