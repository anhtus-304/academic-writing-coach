"""Unit tests for the search aggregator and literature helpers (offline).

These tests do not hit the network: the external sources are monkeypatched and
the helpers are pure functions.
"""
import asyncio

from services.literature_service import _apply_filters, cached_paper_to_dict
from services.search_aggregator import _dedup_key, _relevance_score, search_all


def test_relevance_score_tokens():
    assert _relevance_score("deep learning", "Deep Learning survey", "") > 0.5
    assert _relevance_score("", "anything", "") == 0.5
    assert 0.0 <= _relevance_score("xyz", "abc def ghi jkl", "") <= 1.0


def test_dedup_key():
    a = {"doi": None, "title": "Same Title Here"}
    b = {"doi": None, "title": "same title here"}
    assert _dedup_key(a) == _dedup_key(b)
    c = {"doi": "10.1/x", "title": "other"}
    d = {"doi": " 10.1/X ", "title": "other"}
    assert _dedup_key(c) == _dedup_key(d)


def test_apply_filters():
    papers = [
        {"source": "arxiv", "publication_year": 2024, "doi": "1"},
        {"source": "openalex", "publication_year": 2020, "doi": "2"},
    ]
    src = _apply_filters(papers, {"source": "arxiv"})
    assert len(src) == 1 and src[0]["source"] == "arxiv"
    year = _apply_filters(papers, {"min_year": 2021})
    assert len(year) == 1 and year[0]["publication_year"] == 2024
    assert _apply_filters(papers, None) == papers


def test_cached_paper_to_dict():
    class P:
        id = "u1"
        title = "t"
        authors = "a"
        publication_year = 2024
        source = "arxiv"
        doi = "10.1/x"
        url = "https://e"
        abstract = "abs"
        summary = "tom"
        citation_count = 3
        relevance_score = 0.9

    d = cached_paper_to_dict(P())
    assert d["year"] == 2024 and d["relevance_score"] == 0.9 and d["summary"] == "tom"


def test_aggregator_dedup_and_scoring(monkeypatch):
    async def fake_arxiv(q, limit):
        return [{
            "title": "Shared Paper",
            "authors": "A",
            "abstract": "about deep learning",
            "doi": "10.1/shared",
            "url": "u1",
            "source": "arxiv",
            "publication_year": 2024,
            "citation_count": 1,
            "summary": None,
            "relevance_score": None,
        }]

    async def fake_openalex(q, limit):
        return [{
            "title": "Shared Paper",  # same DOI -> duplicate
            "authors": "A",
            "abstract": "about deep learning",
            "doi": "10.1/shared",
            "url": "u2",
            "source": "openalex",
            "publication_year": 2024,
            "citation_count": 5,
            "summary": None,
            "relevance_score": None,
        }, {
            "title": "Unique Paper",
            "authors": "B",
            "abstract": "machine learning",
            "doi": "10.2/unique",
            "url": "u3",
            "source": "openalex",
            "publication_year": 2023,
            "citation_count": 2,
            "summary": None,
            "relevance_score": None,
        }]

    import services.search_aggregator as agg

    monkeypatch.setattr(agg, "search_arxiv", fake_arxiv)
    monkeypatch.setattr(agg, "search_openalex", fake_openalex)

    async def fake_scholar(q, limit):
        return []

    monkeypatch.setattr(agg, "search_semantic_scholar", fake_scholar)

    results = asyncio.run(search_all("deep learning", limit=10))
    # Shared Paper deduplicated (DOI collision), keeping the higher citation one.
    assert len(results) == 2
    by_title = {p["title"]: p for p in results}
    assert "Shared Paper" in by_title and "Unique Paper" in by_title
    assert by_title["Shared Paper"]["citation_count"] == 5  # openalex version kept
    assert all(p["relevance_score"] is not None for p in results)


def test_aggregator_source_filter(monkeypatch):
    async def fake_arxiv(q, limit):
        return [{
            "title": "arxiv only", "authors": "", "abstract": "",
            "doi": None, "url": None, "source": "arxiv",
            "publication_year": 2024, "citation_count": 0,
            "summary": None, "relevance_score": None,
        }]

    import services.search_aggregator as agg

    monkeypatch.setattr(agg, "search_openalex", lambda q, l: (_ for _ in ()).throw(AssertionError("should not call")))
    monkeypatch.setattr(agg, "search_semantic_scholar", lambda q, l: (_ for _ in ()).throw(AssertionError("should not call")))
    monkeypatch.setattr(agg, "search_arxiv", fake_arxiv)

    results = asyncio.run(search_all("x", limit=5, sources=["arxiv"]))
    assert len(results) == 1 and results[0]["source"] == "arxiv"