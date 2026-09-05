import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional
from xml.etree import ElementTree as ET

import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.config import settings
    from backend.models.cached_paper import CachedPaper
    from backend.models.project import Project
    from backend.models.search_session import SearchSession
    from backend.models.user import User
    from backend.services.credit_service import deduct_credits
    from backend.services.llm_service import llm_service
    from backend.services.search_aggregator import search_all
except ImportError:
    from config import settings
    from models.cached_paper import CachedPaper
    from models.project import Project
    from models.search_session import SearchSession
    from models.user import User
    from services.credit_service import deduct_credits
    from services.llm_service import llm_service
    from services.search_aggregator import search_all

logger = logging.getLogger(__name__)

VALID_SOURCES = ["semantic_scholar", "openalex", "arxiv"]
SEARCH_CREDIT_COST = 1
CACHE_TTL_HOURS = 48
RESULTS_LIMIT = 8

# Mock data used for testing and offline fallback
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


class LiteratureSummarySchema(BaseModel):
    summary_vi: str


def _coerce_list(values: Any) -> List[str]:
    if not values:
        return []
    if isinstance(values, list):
        items = values
    elif isinstance(values, tuple):
        items = list(values)
    else:
        items = [values]

    results: List[str] = []
    for item in items:
        if isinstance(item, str):
            clean = item.strip()
            if clean:
                results.append(clean)
        elif isinstance(item, dict):
            name = item.get("name") or item.get("family") or item.get("given")
            if name:
                results.append(str(name))
            elif item.get("full_name"):
                results.append(str(item["full_name"]))
    return results


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        text = re.sub(r"\s+", " ", value).strip()
        return text or None
    return str(value)


def _normalize_title(item: Dict[str, Any]) -> str:
    title = item.get("title") or item.get("display_name") or item.get("name") or "Untitled"
    return _clean_text(title) or "Untitled"


def _extract_doi(raw: Any) -> Optional[str]:
    if isinstance(raw, dict):
        if raw.get("DOI"):
            return str(raw["DOI"])
        if raw.get("doi"):
            return str(raw["doi"])
    if isinstance(raw, str):
        return raw.strip() or None
    return None


def normalize_paper_record(record: Dict[str, Any], source: str) -> Dict[str, Any]:
    source_name = source.lower()

    if source_name == "semantic_scholar":
        authors = _coerce_list(record.get("authors"))
        title = _normalize_title(record)
        abstract = _clean_text(record.get("abstract"))
        publication_type = _clean_text(record.get("venue")) or "Journal article"
        year = record.get("year")
        doi = _extract_doi(record.get("externalIds")) or _extract_doi(record.get("doi"))
        url = _clean_text(record.get("url"))
        citation_count = record.get("citationCount") or 0
        external_id = record.get("paperId") or record.get("id") or title
        return {
            "id": str(external_id),
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "year": int(year) if isinstance(year, (int, float)) and not isinstance(year, bool) else None,
            "source": source_name,
            "publicationType": publication_type,
            "doi": doi,
            "url": url,
            "citationCount": int(citation_count) if isinstance(citation_count, (int, float)) and not isinstance(citation_count, bool) else 0,
        }

    if source_name == "openalex":
        raw_authors = record.get("authorships") or []
        authors = []
        for item in raw_authors:
            author_obj = item.get("author") or {}
            name = author_obj.get("display_name") or item.get("raw_author_name")
            if name:
                authors.append(str(name).strip())

        title = _normalize_title(record)
        abstract_text = None
        inverted_index = record.get("abstract_inverted_index")
        if isinstance(inverted_index, dict):
            words = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    words.append((pos, word))
            words.sort(key=lambda x: x[0])
            abstract_text = " ".join([word for _, word in words])
        elif isinstance(record.get("abstract"), str):
            abstract_text = record["abstract"]

        primary_loc = record.get("primary_location") or {}
        source_meta = primary_loc.get("source") or {}
        venue = source_meta.get("display_name") or record.get("type_description") or "Scholarly work"
        year = record.get("publication_year")
        doi = _extract_doi(record.get("doi"))
        url = primary_loc.get("landing_page_url") or record.get("id")
        citation_count = record.get("cited_by_count") or 0
        external_id = record.get("id") or title
        return {
            "id": str(external_id),
            "title": title,
            "authors": authors,
            "abstract": _clean_text(abstract_text),
            "year": int(year) if isinstance(year, (int, float)) and not isinstance(year, bool) else None,
            "source": source_name,
            "publicationType": _clean_text(venue) or "Scholarly work",
            "doi": doi,
            "url": _clean_text(url),
            "citationCount": int(citation_count) if isinstance(citation_count, (int, float)) and not isinstance(citation_count, bool) else 0,
        }

    # Default / arXiv normalization
    authors = _coerce_list(record.get("authors"))
    title = _normalize_title(record)
    abstract = _clean_text(record.get("abstract"))
    published = record.get("published")
    year = None
    if isinstance(published, str) and len(published) >= 4:
        try:
            year = int(published[:4])
        except ValueError:
            year = None

    venue = record.get("journal_ref") or "Preprint"
    doi = _extract_doi(record.get("doi"))
    url = record.get("url")
    external_id = record.get("id") or title
    return {
        "id": str(external_id),
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "year": year,
        "source": source_name,
        "publicationType": _clean_text(venue) or "Preprint",
        "doi": doi,
        "url": _clean_text(url),
        "citationCount": 0,
    }


def cached_paper_to_dict(paper: Any) -> dict[str, Any]:
    """Convert a CachedPaper ORM object or duck-typed object into a plain serializable dict."""
    year = getattr(paper, "publication_year", None)
    if year is None:
        year = getattr(paper, "year", None)
    return {
        "id": str(getattr(paper, "id", "")),
        "title": getattr(paper, "title", ""),
        "authors": getattr(paper, "authors", ""),
        "year": year,
        "source": getattr(paper, "source", None),
        "doi": getattr(paper, "doi", None),
        "url": getattr(paper, "url", None),
        "abstract": getattr(paper, "abstract", None),
        "summary": getattr(paper, "summary", None),
        "citation_count": getattr(paper, "citation_count", 0) or 0,
        "relevance_score": getattr(paper, "relevance_score", None),
    }


def _apply_filters(
    papers: list[dict[str, Any]],
    filters: Optional[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply optional search filters (source, min_year) to results."""
    if not filters:
        return papers

    result = papers
    source = filters.get("source")
    if source:
        result = [p for p in result if p.get("source") == source]

    min_year = filters.get("min_year")
    if min_year is not None:
        try:
            threshold = int(min_year)
        except (TypeError, ValueError):
            threshold = None
        if threshold is not None:
            result = [
                p for p in result
                if (p.get("publication_year") is not None and p["publication_year"] >= threshold)
                or (p.get("year") is not None and p["year"] >= threshold)
            ]
    return result


async def _existing_by_doi(db: AsyncSession, papers: list[dict[str, Any]]) -> dict[str, CachedPaper]:
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
    """Fetch papers from live APIs or mock, applying filters + LLM summary."""
    mode = getattr(settings, "LITERATURE_MODE", "auto") or "auto"
    mode = mode.lower()
    sources = _source_list(filters)

    if mode in ("real", "auto"):
        raw = await search_all(query, limit=RESULTS_LIMIT, sources=sources)
        raw = _apply_filters(raw, filters)
        if mode == "real":
            return await _summarize_papers(raw)
        if raw:
            return await _summarize_papers(raw)

    mock_filtered = _apply_filters(MOCK_PAPERS, filters)
    return mock_filtered


async def _summarize_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach a Vietnamese summary to each paper via the LLM (if configured)."""
    if hasattr(llm_service, "is_summarization_enabled"):
        if not llm_service.is_summarization_enabled() or not papers:
            return papers
    elif not papers:
        return papers

    updated: list[dict[str, Any]] = []
    for p in papers:
        summary = p.get("summary")
        if not summary and hasattr(llm_service, "summarize_paper_vietnamese"):
            summary = await llm_service.summarize_paper_vietnamese(p.get("title", ""), p.get("abstract", ""))
        updated.append({**p, "summary": summary or p.get("summary")})
    return updated


async def _fetch_semantic_scholar(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,abstract,venue,year,externalIds,url,citationCount",
    }
    headers = {}
    if getattr(settings, "SEMANTIC_SCHOLAR_API_KEY", None):
        headers["x-api-key"] = settings.SEMANTIC_SCHOLAR_API_KEY

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
    data = payload.get("data") or []
    return [normalize_paper_record(item, "semantic_scholar") for item in data]


async def _fetch_openalex(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    url = "https://api.openalex.org/works"
    params = {
        "search": query,
        "per-page": limit,
        "mailto": "demo@academic-writing-coach.local",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
    data = payload.get("results") or []
    return [normalize_paper_record(item, "openalex") for item in data]


async def _fetch_arxiv(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        xml_text = response.text

    root = ET.fromstring(xml_text)
    records: List[Dict[str, Any]] = []
    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
        title = entry.findtext("{http://www.w3.org/2005/Atom}title", default="")
        summary = entry.findtext("{http://www.w3.org/2005/Atom}summary", default="")
        published = entry.findtext("{http://www.w3.org/2005/Atom}published", default="")
        authors = []
        for author in entry.findall("{http://www.w3.org/2005/Atom}author"):
            author_name = author.findtext("{http://www.w3.org/2005/Atom}name", default="")
            if author_name:
                authors.append(author_name)
        link = None
        for item in entry.findall("{http://www.w3.org/2005/Atom}link"):
            href = item.get("href")
            if href:
                link = href
                break
        records.append({
            "id": entry.findtext("{http://www.w3.org/2005/Atom}id", default=""),
            "title": title,
            "authors": authors,
            "abstract": summary,
            "published": published,
            "url": link,
            "journal_ref": entry.findtext("{http://arxiv.org/schemas/atom}journal_ref", default=""),
        })
    return [normalize_paper_record(item, "arxiv") for item in records]


async def search_direct_literature(
    query: str,
    limit: int = 10,
    sources: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Direct multi-source literature search for Workspace UI and fast retrieval."""
    if not query or not query.strip():
        return []

    selected_sources = sources or VALID_SOURCES
    search_sources = [source.lower() for source in selected_sources if source.lower() in VALID_SOURCES]
    tasks = {
        "semantic_scholar": _fetch_semantic_scholar,
        "openalex": _fetch_openalex,
        "arxiv": _fetch_arxiv,
    }

    aggregated: List[Dict[str, Any]] = []
    for source_name in search_sources:
        try:
            results = await tasks[source_name](query.strip(), limit=limit)
            aggregated.extend(results)
        except Exception as exc:
            logger.warning("Failed to fetch literature from %s: %s", source_name, exc)

    seen: set[str] = set()
    deduplicated: List[Dict[str, Any]] = []
    for item in aggregated:
        key = (item.get("doi") or item.get("url") or item.get("title") or "unknown").lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduplicated.append(item)

    return deduplicated[:limit * 3]


async def summarize_paper(paper: Dict[str, Any]) -> str:
    """Summarize academic paper into Vietnamese using LLM."""
    if not settings.OPENROUTER_API_KEY or settings.OPENROUTER_API_KEY == "your_api_key":
        raise ValueError("OpenRouter API key chưa được cấu hình. Vui lòng thêm khóa API OpenRouter vào backend/.env.")

    title = _clean_text(paper.get("title")) or "Bài báo khoa học"
    abstract = _clean_text(paper.get("abstract")) or "Không có tóm tắt văn bản đầy đủ, nên tổng hợp nội dung chính dựa trên tiêu đề và nguồn tài liệu."
    authors = ", ".join(paper.get("authors") or [])

    system_prompt = (
        "Bạn là trợ lý nghiên cứu học thuật. Viết tóm tắt bằng tiếng Việt ngắn gọn, chính xác và học thuật. "
        "Giữ nguyên ý nghĩa, nhấn mạnh mục tiêu, phương pháp và đóng góp chính."
    )
    user_prompt = (
        f"Tiêu đề: {title}\n"
        f"Tác giả: {authors or 'Không rõ'}\n"
        f"Tóm tắt gốc: {abstract}\n\n"
        "Hãy trả về một bản tóm tắt tiếng Việt 3-5 câu, rõ ràng và phù hợp cho người học/giảng viên."
    )

    result = await llm_service.generate_structured_output(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema=LiteratureSummarySchema,
        temperature=0.2,
    )
    return result.summary_vi.strip()


async def search_project_literature(
    db: AsyncSession,
    project: Project,
    query: str,
    filters: Optional[dict[str, Any]],
    current_user: User,
) -> dict[str, Any]:
    """Search academic literature for a project with 48h DB caching and credit deduction.

    Returns cached results when a non-expired SearchSession exists for the same
    project + query; otherwise fetches new results, stores them in CachedPaper,
    creates a fresh SearchSession and deducts a credit.
    """
    now = datetime.now(timezone.utc)

    # 1. Check for a valid (non-expired) cache entry
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
                CachedPaper.session_id == cached_session.id
            )
        )
        cached_papers = papers_result.scalars().all()
        return {
            "search_session_id": str(cached_session.id),
            "cached": True,
            "papers": [cached_paper_to_dict(p) for p in cached_papers],
        }

    # 2. No cache hit: deduct a credit before performing search
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

    # 3. Fetch results (mock or live APIs) and create a new search session
    raw_papers = await _fetch_source_papers(query, filters)
    new_session = SearchSession(
        project_id=project.id,
        query=query,
        filters=filters,
        total_results=len(raw_papers),
        expires_at=now + timedelta(hours=CACHE_TTL_HOURS),
    )
    db.add(new_session)
    await db.flush()

    # 4. Persist papers, reusing any already-cached paper by doi
    by_doi = await _existing_by_doi(db, raw_papers)
    stored_papers: list[CachedPaper] = []
    for item in raw_papers:
        if item.get("doi") and item["doi"] in by_doi:
            returned = by_doi[item["doi"]]
        else:
            paper = CachedPaper(
                session_id=new_session.id,
                title=item.get("title") or "Untitled",
                authors=item.get("authors"),
                abstract=item.get("abstract"),
                doi=item.get("doi"),
                url=item.get("url"),
                source=item.get("source"),
                year=item.get("publication_year") or item.get("year"),
                citation_count=item.get("citation_count") or 0,
                summary=item.get("summary"),
                relevance_score=item.get("relevance_score") or 0.0,
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


# Dual interface for search_literature: supports both direct search and project-scoped search
async def search_literature(*args, **kwargs) -> Any:
    if args and isinstance(args[0], AsyncSession) or "db" in kwargs:
        return await search_project_literature(*args, **kwargs)
    return await search_direct_literature(*args, **kwargs)
