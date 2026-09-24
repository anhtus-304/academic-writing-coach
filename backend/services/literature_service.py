import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional
from xml.etree import ElementTree as ET

import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.config import settings
    from backend.models.cached_paper import CachedPaper
    from backend.models.project import Project
    from backend.models.search_session import SearchSession
    from backend.models.selected_paper import SelectedPaper
    from backend.models.user import User
    from backend.services.ai_use_logger import ai_use_logger
    from backend.services.credit_service import deduct_credits
    from backend.services.llm_service import llm_service
    from backend.services.search_aggregator import search_all
    from backend.services.citation_formatter import CitationFormatterService
    from backend.schemas.citation_schemas import CitationMetadataSchema, CitationStyle, DocumentType
except ImportError:
    from config import settings
    from models.cached_paper import CachedPaper
    from models.project import Project
    from models.search_session import SearchSession
    from models.selected_paper import SelectedPaper
    from models.user import User
    from services.ai_use_logger import ai_use_logger
    from services.credit_service import deduct_credits
    from services.llm_service import llm_service
    from services.search_aggregator import search_all
    from services.citation_formatter import CitationFormatterService
    from schemas.citation_schemas import CitationMetadataSchema, CitationStyle, DocumentType


logger = logging.getLogger(__name__)

VALID_SOURCES = ["semantic_scholar", "openalex", "arxiv"]
SEARCH_CREDIT_COST = 1
CACHE_TTL_HOURS = 48
RESULTS_LIMIT = 8

# Mock data used for testing and offline fallback
MOCK_PAPERS: list[dict[str, Any]] = [
    {
        "title": "Deep Learning Approaches for Automated Essay Scoring",
        "authors": ["Nguyen Van An", "Le Thi B"],
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
        "authors": ["Tran Minh C", "Pham Quoc D"],
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
        "authors": ["Hoang Thanh E"],
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

    raw_authors = getattr(paper, "authors", None)
    authors_list: list[str] = []
    if isinstance(raw_authors, list):
        for a in raw_authors:
            if isinstance(a, dict):
                name = a.get("name") or a.get("family") or a.get("full_name")
                if name:
                    authors_list.append(str(name).strip())
            elif a:
                authors_list.append(str(a).strip())
    elif isinstance(raw_authors, str) and raw_authors.strip():
        authors_list = [a.strip() for a in raw_authors.split(",") if a.strip()]
    elif raw_authors:
        authors_list = [str(raw_authors).strip()]

    return {
        "id": str(getattr(paper, "id", "")),
        "title": getattr(paper, "title", ""),
        "authors": authors_list,
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
    """Return a map doi -> CachedPaper for any paper with a non-empty doi.

    Used by :func:`search_project_literature` to avoid re-summarizing a paper
    that was already cached by an earlier search session.
    """
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


async def fetch_candidate_papers(
    query: str,
    limit: int = 5,
    filters: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Public, cache-free paper fetcher used by the LangGraph literature node.

    Honours ``settings.LITERATURE_MODE`` through :func:`_fetch_source_papers`:
    ``mock`` returns the deterministic offline corpus (used by unit tests) while
    ``real``/``auto`` query the live APIs.
    """
    if not query or not query.strip():
        return []

    papers = await _fetch_source_papers(query.strip(), filters)
    if limit and limit > 0:
        return list(papers)[:limit]
    return list(papers)


async def full_text_search_papers(
    db: AsyncSession,
    query: str,
    limit: int = 20,
) -> list[CachedPaper]:
    """Full-text search over ``cached_papers.title + abstract``.

    On PostgreSQL this uses the GIN index created by migration
    ``f3a91c2d7b64`` (``to_tsvector('simple', title || ' ' || abstract)``), which
    keeps lookups in the sub-50ms range once the literature cache grows. Other
    dialects (SQLite in tests) transparently fall back to a portable ``ILIKE``
    scan so the same code path remains testable offline.
    """
    term = (query or "").strip()
    stmt = select(CachedPaper)

    try:
        dialect = db.get_bind().dialect.name
    except Exception:  # pragma: no cover - defensive
        dialect = ""

    if term:
        if dialect == "postgresql":
            document = func.to_tsvector(
                "simple",
                func.coalesce(CachedPaper.title, "") + " " + func.coalesce(CachedPaper.abstract, ""),
            )
            stmt = stmt.where(document.op("@@")(func.plainto_tsquery("simple", term)))
        else:
            pattern = f"%{term}%"
            stmt = stmt.where(
                or_(
                    CachedPaper.title.ilike(pattern),
                    CachedPaper.abstract.ilike(pattern),
                )
            )

    stmt = stmt.order_by(CachedPaper.relevance_score.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _summarize_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach a Vietnamese summary to each paper via the LLM (if configured) or abstract snippet."""
    if not papers:
        return papers

    updated: list[dict[str, Any]] = []
    for p in papers:
        summary = p.get("summary")
        if not summary and hasattr(llm_service, "summarize_paper_vietnamese"):
            try:
                summary = await llm_service.summarize_paper_vietnamese(p.get("title", ""), p.get("abstract", ""))
            except Exception:
                summary = None
        if not summary and p.get("abstract"):
            abs_text = str(p["abstract"]).strip()
            summary = abs_text[:280] + "..." if len(abs_text) > 280 else abs_text
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
    enable_semantic_expansion: bool = True,
    return_expanded_queries: bool = False,
) -> Any:
    """Direct multi-source literature search for Workspace UI and fast retrieval with semantic expansion."""
    if not query or not query.strip():
        return ([], []) if return_expanded_queries else []

    selected_sources = sources or VALID_SOURCES
    search_sources = [source.lower() for source in selected_sources if source.lower() in VALID_SOURCES]
    tasks = {
        "semantic_scholar": _fetch_semantic_scholar,
        "openalex": _fetch_openalex,
        "arxiv": _fetch_arxiv,
    }

    expanded_queries: List[str] = [query.strip()]

    # If semantic expansion is enabled, generate 3-5 academic queries using LiteratureAgent
    if enable_semantic_expansion:
        try:
            try:
                from backend.agents.literature_agent import literature_agent
            except ImportError:
                from agents.literature_agent import literature_agent

            gen_res = await literature_agent.generate_queries(topic=query.strip(), num_queries=3)
            generated = [q.strip() for q in (gen_res.queries or []) if q and q.strip()]
            if not generated and gen_res.search_queries:
                generated = [item.query.strip() for item in gen_res.search_queries if item.query and item.query.strip()]
            for gq in generated:
                if gq.lower() not in [eq.lower() for eq in expanded_queries]:
                    expanded_queries.append(gq)
        except Exception as exc:
            logger.warning("Semantic query expansion fallback: %s", exc)

    queries_to_search = expanded_queries[:3]  # Search top queries concurrently

    async def fetch_source_queries(source_name: str) -> List[Dict[str, Any]]:
        source_results: List[Dict[str, Any]] = []
        for q in queries_to_search:
            try:
                res = await tasks[source_name](q, limit=limit)
                source_results.extend(res)
            except Exception as exc:
                logger.warning("Failed to fetch literature from %s for query '%s': %s", source_name, q, exc)
        return source_results

    fetch_tasks = [fetch_source_queries(s) for s in search_sources if s in tasks]
    gathered = await asyncio.gather(*fetch_tasks, return_exceptions=True)

    aggregated: List[Dict[str, Any]] = []
    for item in gathered:
        if isinstance(item, list):
            aggregated.extend(item)

    try:
        from backend.services.search_aggregator import _relevance_score
    except ImportError:
        try:
            from services.search_aggregator import _relevance_score
        except ImportError:
            def _relevance_score(q, t, a): return 0.5

    seen: set[str] = set()
    deduplicated: List[Dict[str, Any]] = []
    for item in aggregated:
        key = (item.get("doi") or item.get("url") or item.get("title") or "unknown").lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        rel = _relevance_score(query, item.get("title") or "", item.get("abstract") or "")
        item["relevanceScore"] = round(rel, 2)
        deduplicated.append(item)

    # Sort by relevanceScore and citationCount descending
    deduplicated.sort(
        key=lambda x: (x.get("relevanceScore") or 0.0, x.get("citationCount") or x.get("citation_count") or 0),
        reverse=True,
    )

    final_papers = deduplicated[:limit * 2]
    if return_expanded_queries:
        return final_papers, expanded_queries
    return final_papers


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


def _paper_to_citation_metadata(paper_data: dict[str, Any]) -> CitationMetadataSchema:
    authors_raw = paper_data.get("authors") or []
    if isinstance(authors_raw, str):
        authors = [a.strip() for a in authors_raw.split(",") if a.strip()]
    elif isinstance(authors_raw, list):
        authors = [str(a).strip() for a in authors_raw if a]
    else:
        authors = ["Tác giả"]
    if not authors:
        authors = ["Tác giả"]

    year = paper_data.get("year") or paper_data.get("publication_year") or 2024
    try:
        year_int = int(year)
    except (ValueError, TypeError):
        year_int = 2024

    return CitationMetadataSchema(
        title=paper_data.get("title") or "Tài liệu tham khảo",
        authors=authors,
        year=year_int,
        journal=paper_data.get("publicationType") or paper_data.get("venue") or paper_data.get("source"),
        doi=paper_data.get("doi"),
        url=paper_data.get("url"),
        doc_type=DocumentType.JOURNAL,
    )


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
    creates a fresh SearchSession and deducts 1 credit.
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
        saved_filters = cached_session.filters if isinstance(cached_session.filters, dict) else {}
        expanded_queries = saved_filters.get("expanded_queries") or [query]
        return {
            "search_session_id": str(cached_session.id),
            "cached": True,
            "total_results": len(cached_papers),
            "expanded_queries": expanded_queries,
            "papers": [cached_paper_to_dict(p) for p in cached_papers],
        }

    # 2. No cache hit: deduct 1 credit before performing search
    deducted = await deduct_credits(
        db,
        current_user,
        SEARCH_CREDIT_COST,
        f"Literature search: {query}",
    )
    if not deducted:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Số dư credit không đủ để thực hiện tìm kiếm tài liệu mới.",
        )

    # 3. Query expansion with LiteratureAgent
    expanded_queries = [query.strip()]
    try:
        try:
            from backend.agents.literature_agent import literature_agent
        except ImportError:
            from agents.literature_agent import literature_agent

        gen_res = await literature_agent.generate_queries(topic=query.strip(), num_queries=3)
        generated = [q.strip() for q in (gen_res.queries or []) if q and q.strip()]
        for gq in generated:
            if gq.lower() not in [eq.lower() for eq in expanded_queries]:
                expanded_queries.append(gq)
    except Exception as exc:
        logger.warning("Semantic query expansion fallback: %s", exc)

    # 4. Fetch results (mock or live APIs) and create a new search session
    raw_papers = await _fetch_source_papers(query, filters)
    session_filters = {"filters": filters, "expanded_queries": expanded_queries}
    new_session = SearchSession(
        project_id=project.id,
        query=query,
        filters=session_filters,
        total_results=len(raw_papers),
        expires_at=now + timedelta(hours=CACHE_TTL_HOURS),
    )
    db.add(new_session)
    await db.flush()

    # 5. Persist papers. A CachedPaper row belongs to exactly one SearchSession,
    #    therefore every session must own a self-contained result set - the
    #    cache-hit path and ``/literature/recent-search`` both read papers by
    #    ``session_id``. Papers already cached by a *previous* session are copied
    #    (reusing their Vietnamese summary so no second LLM call is needed),
    #    while duplicates inside this same batch reuse the row just created.
    known_by_doi = await _existing_by_doi(db, raw_papers)
    stored_papers: list[CachedPaper] = []
    for item in raw_papers:
        doi = item.get("doi")
        existing = known_by_doi.get(doi) if doi else None
        if existing is not None and existing.session_id == new_session.id:
            stored_papers.append(existing)
            continue

        paper = CachedPaper(
            session_id=new_session.id,
            title=item.get("title") or "Untitled",
            authors=item.get("authors"),
            abstract=item.get("abstract"),
            doi=doi,
            url=item.get("url") or (existing.url if existing else None),
            source=item.get("source") or (existing.source if existing else None),
            year=(
                item.get("publication_year")
                or item.get("year")
                or (existing.year if existing else None)
            ),
            citation_count=item.get("citation_count") or (existing.citation_count if existing else 0),
            summary=item.get("summary") or (existing.summary if existing else None),
            relevance_score=item.get("relevance_score") or (existing.relevance_score if existing else 0.0),
        )
        db.add(paper)
        if doi:
            known_by_doi[doi] = paper
        stored_papers.append(paper)

    # 6. Log AI use
    try:
        await ai_use_logger.log_ai_usage(
            agent_name="LiteratureAgent",
            tokens_used=120,
            user_id=str(current_user.id),
            project_id=str(project.id),
            input_summary={"query": query, "filters": filters},
            output_summary={"total_results": len(stored_papers)},
            credits_charged=SEARCH_CREDIT_COST,
            db=db,
        )
    except Exception as log_err:
        logger.warning("Failed to log AI use for LiteratureAgent: %s", log_err)

    await db.commit()

    return {
        "search_session_id": str(new_session.id),
        "cached": False,
        "total_results": len(stored_papers),
        "expanded_queries": expanded_queries,
        "papers": [cached_paper_to_dict(p) for p in stored_papers],
    }


async def select_paper_for_project(
    db: AsyncSession,
    project: Project,
    paper_data: Optional[dict[str, Any]] = None,
    cached_paper_id: Optional[str] = None,
    relevant_sections: Optional[list[str]] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """Persist a chosen paper into the project's permanent selected_papers table."""
    target_cached_paper: Optional[CachedPaper] = None

    if cached_paper_id:
        target_cached_paper = await db.get(CachedPaper, cached_paper_id)

    if target_cached_paper is None and paper_data:
        # Check if paper with matching doi/url already exists
        doi = paper_data.get("doi")
        url = paper_data.get("url")
        if doi:
            res = await db.execute(select(CachedPaper).where(CachedPaper.doi == doi))
            target_cached_paper = res.scalars().first()
        elif url:
            res = await db.execute(select(CachedPaper).where(CachedPaper.url == url))
            target_cached_paper = res.scalars().first()

        if target_cached_paper is None:
            # Need an existing session or create a placeholder session
            res_sess = await db.execute(
                select(SearchSession)
                .where(SearchSession.project_id == project.id)
                .order_by(SearchSession.created_at.desc())
            )
            sess = res_sess.scalars().first()
            if not sess:
                sess = SearchSession(
                    project_id=project.id,
                    query=paper_data.get("title") or "Direct Selection",
                    filters={},
                    total_results=1,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                )
                db.add(sess)
                await db.flush()

            target_cached_paper = CachedPaper(
                session_id=sess.id,
                title=paper_data.get("title") or "Untitled",
                authors=paper_data.get("authors") or [],
                abstract=paper_data.get("abstract"),
                doi=doi,
                url=url,
                source=paper_data.get("source"),
                year=paper_data.get("year") or paper_data.get("publication_year"),
                citation_count=paper_data.get("citation_count") or paper_data.get("citationCount") or 0,
                summary=paper_data.get("summary") or paper_data.get("summaryVi"),
                relevance_score=paper_data.get("relevance_score") or paper_data.get("relevanceScore") or 0.0,
            )
            db.add(target_cached_paper)
            await db.flush()

    if target_cached_paper is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không tìm thấy thông tin bài báo để lưu vào đề tài.",
        )

    # Check if already selected
    existing_stmt = select(SelectedPaper).where(
        SelectedPaper.project_id == project.id,
        SelectedPaper.cached_paper_id == target_cached_paper.id,
    )
    existing_res = await db.execute(existing_stmt)
    existing_selected = existing_res.scalars().first()

    # Format citation according to project's citation style
    paper_dict = cached_paper_to_dict(target_cached_paper)
    meta = _paper_to_citation_metadata(paper_dict)
    raw_style = (getattr(project, "citation_style", None) or "apa7").lower()
    style_map = {
        "apa7": CitationStyle.APA7,
        "ieee": CitationStyle.IEEE,
        "bgddt": CitationStyle.BGDDT,
    }
    target_style = style_map.get(raw_style, CitationStyle.APA7)
    citation_res = CitationFormatterService.format_citation(meta, style=target_style)
    formatted_citation = citation_res.full_citation

    if existing_selected is not None:
        if notes is not None:
            existing_selected.notes = notes
        if relevant_sections is not None:
            existing_selected.relevant_sections = relevant_sections
        existing_selected.citation_formatted = formatted_citation
        await db.commit()
        await db.refresh(existing_selected)
        item = existing_selected
    else:
        new_selected = SelectedPaper(
            project_id=project.id,
            cached_paper_id=target_cached_paper.id,
            relevant_sections=relevant_sections,
            citation_formatted=formatted_citation,
            used_in_draft=False,
            notes=notes,
        )
        db.add(new_selected)
        await db.commit()
        await db.refresh(new_selected)
        item = new_selected

    return {
        "id": str(item.id),
        "project_id": str(item.project_id),
        "cached_paper_id": str(item.cached_paper_id),
        "relevant_sections": item.relevant_sections,
        "citation_formatted": item.citation_formatted,
        "used_in_draft": bool(item.used_in_draft),
        "notes": item.notes,
        "selected_at": item.selected_at.isoformat() if item.selected_at else None,
        "paper": paper_dict,
    }


async def get_project_selected_papers(db: AsyncSession, project_id: str) -> dict[str, Any]:
    """Retrieve all permanently selected papers for a given project."""
    stmt = (
        select(SelectedPaper)
        .where(SelectedPaper.project_id == project_id)
        .order_by(SelectedPaper.selected_at.desc())
    )
    result = await db.execute(stmt)
    selected_list = result.scalars().all()

    items = []
    for sp in selected_list:
        cached_paper = await db.get(CachedPaper, sp.cached_paper_id)
        paper_dict = cached_paper_to_dict(cached_paper) if cached_paper else None
        items.append({
            "id": str(sp.id),
            "project_id": str(sp.project_id),
            "cached_paper_id": str(sp.cached_paper_id),
            "relevant_sections": sp.relevant_sections,
            "citation_formatted": sp.citation_formatted,
            "used_in_draft": bool(sp.used_in_draft),
            "notes": sp.notes,
            "selected_at": sp.selected_at.isoformat() if sp.selected_at else None,
            "paper": paper_dict,
        })
    return {
        "total": len(items),
        "selected_papers": items,
    }


async def remove_selected_paper(db: AsyncSession, project_id: str, selected_paper_id: str) -> bool:
    """Remove a selected paper from the project."""
    stmt = select(SelectedPaper).where(
        SelectedPaper.id == selected_paper_id,
        SelectedPaper.project_id == project_id,
    )
    result = await db.execute(stmt)
    item = result.scalars().first()
    if not item:
        return False
    await db.delete(item)
    await db.commit()
    return True


async def get_recent_search_session(db: AsyncSession, project_id: str) -> dict[str, Any]:
    """Retrieve the most recent active (unexpired < 48h) search session for the project."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(SearchSession)
        .where(
            SearchSession.project_id == project_id,
            SearchSession.expires_at > now,
        )
        .order_by(SearchSession.created_at.desc())
    )
    result = await db.execute(stmt)
    recent = result.scalars().first()
    if not recent:
        return {
            "has_recent": False,
            "search_session_id": None,
            "query": None,
            "total_results": 0,
            "expires_at": None,
            "papers": [],
        }

    papers_stmt = select(CachedPaper).where(CachedPaper.session_id == recent.id)
    papers_res = await db.execute(papers_stmt)
    cached_papers = papers_res.scalars().all()
    return {
        "has_recent": True,
        "search_session_id": str(recent.id),
        "query": recent.query,
        "total_results": len(cached_papers),
        "expires_at": recent.expires_at.isoformat() if recent.expires_at else None,
        "papers": [cached_paper_to_dict(p) for p in cached_papers],
    }


# Dual interface for search_literature: supports both direct search and project-scoped search
async def search_literature(*args, **kwargs) -> Any:
    if args and isinstance(args[0], AsyncSession) or "db" in kwargs:
        return await search_project_literature(*args, **kwargs)
    return await search_direct_literature(*args, **kwargs)

