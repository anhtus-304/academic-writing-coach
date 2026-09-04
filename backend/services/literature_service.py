import asyncio
import logging
import re
from typing import Any, Dict, Iterable, List, Optional
from xml.etree import ElementTree as ET

import httpx
from pydantic import BaseModel

try:
    from backend.config import settings
    from backend.services.llm_service import llm_service
except ImportError:
    from config import settings
    from services.llm_service import llm_service

logger = logging.getLogger(__name__)

VALID_SOURCES = ["semantic_scholar", "openalex", "arxiv"]


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
            "raw": record,
        }

    if source_name == "openalex":
        authors = []
        for author in record.get("authorships") or []:
            raw_author = author.get("author") or {}
            name = raw_author.get("display_name") or raw_author.get("name")
            if name:
                authors.append(str(name))

        title = _normalize_title(record)
        abstract = None
        abstract_source = record.get("abstract_inverted_index")
        if isinstance(abstract_source, dict):
            ordered = sorted(abstract_source.items(), key=lambda item: int(item[0]))
            abstract = "".join([value for _, value in ordered])
        abstract = abstract or _clean_text(record.get("abstract"))
        year = record.get("publication_year") or record.get("year")
        venue = record.get("primary_location") or {}
        venue_name = (venue.get("source") or {}).get("display_name")
        publication_type = venue_name or "Journal article"
        best_url = _clean_text(record.get("landing_page_url")) or _clean_text(record.get("primary_location", {}).get("landing_page_url"))
        doi = _extract_doi(record.get("doi"))
        DOI_VALUE = doi or (record.get("ids") or {}).get("doi")
        citation_count = record.get("cited_by_count") or 0
        external_id = record.get("id") or record.get("openalex") or title
        return {
            "id": str(external_id),
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "year": int(year) if isinstance(year, (int, float)) and not isinstance(year, bool) else None,
            "source": source_name,
            "publicationType": publication_type,
            "doi": DOI_VALUE,
            "url": best_url,
            "citationCount": int(citation_count) if isinstance(citation_count, (int, float)) and not isinstance(citation_count, bool) else 0,
            "raw": record,
        }

    if source_name == "arxiv":
        authors = _coerce_list(record.get("authors"))
        title = _normalize_title(record)
        abstract = _clean_text(record.get("abstract")) or _clean_text(record.get("summary"))
        year = None
        published = record.get("published")
        if published and isinstance(published, str):
            match = re.search(r"(\d{4})-\d{2}-\d{2}", published)
            if match:
                year = int(match.group(1))
        publication_type = _clean_text(record.get("journal_ref")) or "Preprint"
        doi = _clean_text(record.get("doi"))
        url = _clean_text(record.get("url")) or _clean_text(record.get("link"))
        citation_count = record.get("citationCount") or 0
        external_id = record.get("id") or record.get("arxiv_id") or title
        return {
            "id": str(external_id),
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "year": year,
            "source": source_name,
            "publicationType": publication_type,
            "doi": doi,
            "url": url,
            "citationCount": int(citation_count) if isinstance(citation_count, (int, float)) and not isinstance(citation_count, bool) else 0,
            "raw": record,
        }

    return {
        "id": str(record.get("id") or record.get("paperId") or record.get("title", "unknown")),
        "title": _normalize_title(record),
        "authors": _coerce_list(record.get("authors")),
        "abstract": _clean_text(record.get("abstract")),
        "year": record.get("year"),
        "source": source_name,
        "publicationType": _clean_text(record.get("publicationType")) or "Article",
        "doi": _extract_doi(record.get("doi")) or _extract_doi(record.get("externalIds")),
        "url": _clean_text(record.get("url")),
        "citationCount": record.get("citationCount") or 0,
        "raw": record,
    }


async def _fetch_semantic_scholar(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "paperId,title,abstract,authors,year,venue,url,externalIds,citationCount",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, params=params)
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


async def search_literature(query: str, limit: int = 10, sources: Optional[List[str]] = None) -> List[Dict[str, Any]]:
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
