from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.cached_paper import CachedPaper
from models.project import Project
from models.search_session import SearchSession
from models.user import User
from services import llm_service
from services.credit_service import deduct_credits
from services.search_aggregator import search_all

SEARCH_CREDIT_COST = 1
CACHE_TTL_HOURS = 48
RESULTS_LIMIT = 8

# Mock data used for testing. Will be replaced by real API integration
# with Semantic Scholar, arXiv and OpenAlex.
MOCK_PAPERS: list[dict[str, Any]] = [
    {
        "title": "Deep Learning Approaches for Automated Essay Scoring",
        "authors": "Nguyen Van An, Le Thi B",
        "abstract": "This paper surveys deep learning techniques applied to automated essay scoring...",
        "doi": "10.1145/example.essay.2023",
        "url": "https://doi.org/10.1145/example.essay.2023",
        "source": "semantic_scholar",
        "publication_year": 2023,
        "citation_count": 142,
        "summary": "Bai bao khao sat cac ky thuat hoc sau dung de cham diem bai luan tu dong...",
        "relevance_score": 0.92,
    },
    {
        "title": "Large Language Models as Academic Writing Assistants: A Survey",
        "authors": "Tran Minh C, Pham Quoc D",
        "abstract": "We review the role of large language models in supporting academic writing...",
        "doi": "10.48550/arXiv.2310.00001",
        "url": "https://arxiv.org/abs/2310.00001",
        "source": "arxiv",
        "publication_year": 2024,
        "citation_count": 87,
        "summary": "Bai bao tong quan vai tro cua mo hinh ngon ngu lon trong viec ho tro viet hoc thuat...",
        "relevance_score": 0.88,
    },
    {
        "title": "Citation Network Analysis for Academic Literature Discovery",
        "authors": "Hoang Thanh E",
        "abstract": "This work proposes a citation-aware retrieval method to improve literature discovery...",
        "doi": "10.1016/j.example.citation.2022",
        "url": "https://doi.org/10.1016/j.example.citation.2022",
        "source": "openalex",
        "publication_year": 2022,
        "citation_count": 45,
        "summary": "Cong trinh de xuat phuong phap truy hoi dua tren mang trich dan nham cai thien viec kham pha tai lieu...",
        "relevance_score": 0.81,
    },
]


def cached_paper_to_dict(paper: CachedPaper) -> dict[str, Any]:
    """Convert a CachedPaper ORM object into a plain serializable dict."""
    return {
        "id": str(paper.id),
        "title": paper.title,
        "authors": paper.authors,
        "year": paper.publication_year,
        "source": paper.source,
        "doi": paper.doi,
        "url": paper.url,
        "abstract": paper.abstract,
        "summary": paper.summary,
        "citation_count": paper.citation_count,
        "relevance_score": paper.relevance_score,
    }


def _apply_filters(
    papers: list[dict[str, Any]],
    filters: Optional[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply optional search filters (e.g. source, min_year) to mock results."""
    if not filters:
        return papers

    result = papers
    source = filters.get("source")
    if source:
        result = [p for p in result if p["source"] == source]

    min_year = filters.get("min_year")
    if min_year is not None:
        try:
            threshold = int(min_year)
        except (TypeError, ValueError):
            threshold = None
        if threshold is not None:
            result = [
                p for p in result
                if p["publication_year"] is not None
                and p["publication_year"] >= threshold
            ]
    return result


async def _existing_by_doi(db: AsyncSession, papers) -> dict[str, CachedPaper]:
    """Return a map doi -> CachedPaper for any paper with a non-empty doi."""
    dois = [p["doi"] for p in papers if p.get("doi")]
    if not dois:
        return {}
    result = await db.execute(select(CachedPaper).where(CachedPaper.doi.in_(dois)))
    return {p.doi: p for p in result.scalars().all() if p.doi}


def _source_list(filters: Optional[dict[str, Any]]) -> list[str] | None:
    """Extract the list of requested sources from filters, if any."""
    if not filters or not filters.get("source"):
        return None
    source = filters["source"]
    if isinstance(source, str):
        return [source]
    if isinstance(source, list):
        return [s for s in source if isinstance(s, str)]
    return None


async def _fetch_source_papers(
    query: str,
    filters: Optional[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fetch papers from live APIs or mock, applying filters + LLM summary.

    ``settings.LITERATURE_MODE``:
      - "mock": always return mock data (used by tests).
      - "real": only live API results (may return [] if sources fail).
      - "auto" (default): try live, fall back to mock when nothing is returned.
    """
    mode = (settings.LITERATURE_MODE or "auto").lower()
    sources = _source_list(filters)

    if mode in ("real", "auto"):
        raw = await search_all(query, limit=RESULTS_LIMIT, sources=sources)
        raw = _apply_filters(raw, filters)
        if mode == "real":
            return await _summarize_papers(raw)

    mock_filtered = _apply_filters(MOCK_PAPERS, filters)
    return mock_filtered


async def _summarize_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach a Vietnamese summary to each paper via the LLM (if configured)."""
    if not llm_service.is_summarization_enabled() or not papers:
        return papers
    updated: list[dict[str, Any]] = []
    for p in papers:
        summary = await llm_service.summarize_paper_vietnamese(p["title"], p["abstract"])
        updated.append({**p, "summary": summary})
    return updated
async def search_literature(
    db: AsyncSession,
    project: Project,
    query: str,
    filters: Optional[dict[str, Any]],
    current_user: User,
) -> dict[str, Any]:
    """Search academic literature for a project.

    Returns cached results when a non-expired SearchSession exists for the same
    project + query; otherwise fetches new results, stores them in CachedPaper,
    creates a fresh SearchSession and deducts a credit.
    """
    now = datetime.now(timezone.utc)

    # 1. Check for a valid (non-expired) cache entry.
    cache_result = await db.execute(
        select(SearchSession)
        .where(
            SearchSession.project_id == project.id,
            SearchSession.query == query,
            SearchSession.expires_at > now,
        )
        .order_by(SearchSession.created_at.desc())
    )
    cached_session = cache_result.scalars().first()
    if cached_session is not None:
        papers_result = await db.execute(
            select(CachedPaper).where(
                CachedPaper.search_session_id == cached_session.id
            )
        )
        cached_papers = papers_result.scalars().all()
        return {
            "search_session_id": str(cached_session.id),
            "cached": True,
            "papers": [cached_paper_to_dict(p) for p in cached_papers],
        }

    # 2. No cache hit: deduct a credit before performing the search.
    deducted = await deduct_credits(
        db,
        current_user,
        SEARCH_CREDIT_COST,
        f"Literature search: {query}",
    )
    if not deducted:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits to perform the search",
        )

    # 3. Fetch results (mock or live APIs) and create a new search session.
    raw_papers = await _fetch_source_papers(query, filters)
    new_session = SearchSession(
        project_id=project.id,
        query=query,
        search_engine="aggregated",
        created_at=now,
        expires_at=now + timedelta(hours=CACHE_TTL_HOURS),
    )
    db.add(new_session)
    await db.flush()

    # 4. Persist papers, reusing any already-cached paper (doi is unique).
    by_doi = await _existing_by_doi(db, raw_papers)
    stored_papers: list[CachedPaper] = []
    for item in raw_papers:
        if item.get("doi") and item["doi"] in by_doi:
            returned = by_doi[item["doi"]]
        else:
            paper = CachedPaper(
                search_session_id=new_session.id,
                title=item["title"],
                authors=item["authors"],
                abstract=item["abstract"],
                doi=item["doi"],
                url=item["url"],
                source=item["source"],
                publication_year=item["publication_year"],
                citation_count=item["citation_count"],
                summary=item["summary"],
                relevance_score=item["relevance_score"],
            )
            db.add(paper)
            if item.get("doi"):
                by_doi[item["doi"]] = paper
            returned = paper
        stored_papers.append(returned)

    await db.commit()

    return {
        "search_session_id": str(new_session.id),
        "cached": False,
        "papers": [cached_paper_to_dict(p) for p in stored_papers],
    }