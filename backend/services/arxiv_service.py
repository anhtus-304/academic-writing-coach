import re
import logging
from typing import List, Optional
import httpx

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    from schemas.literature_schemas import AuthorSchema, PaperSource, PaperSchema
except ImportError:
    from backend.schemas.literature_schemas import AuthorSchema, PaperSchema, PaperSource

try:
    from config import settings
except ImportError:
    from backend.config import settings

logger = logging.getLogger(__name__)


class ArxivService:
    """Client for querying academic papers from the arXiv API."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        timeout: float = 12.0,
    ):
        self.api_url = api_url or settings.ARXIV_API_URL
        self.timeout = timeout

    async def search(
        self,
        query: str,
        limit: int = 10,
        start: int = 0,
    ) -> List[PaperSchema]:
        """Search papers from arXiv matching the given query."""
        if not query or not query.strip():
            return []

        clean_query = query.strip()
        # Format arXiv search query
        search_query = f"all:{clean_query}"

        params = {
            "search_query": search_query,
            "start": start,
            "max_results": min(max(1, limit), 100),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        headers = {
            "User-Agent": "AcademicWritingCoach/1.0 (academic-research-tool)",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.api_url,
                    params=params,
                    headers=headers,
                )

                if response.status_code != 200:
                    logger.warning(
                        f"arXiv API returned status {response.status_code}: {response.text[:200]}"
                    )
                    return []

                return self._parse_feed(response.text)

        except httpx.TimeoutException:
            logger.warning(f"arXiv API timed out after {self.timeout}s for query: '{query}'")
            return []
        except Exception as e:
            logger.error(f"arXiv search error: {e}", exc_info=True)
            return []

    def _clean_text(self, text: Optional[str]) -> Optional[str]:
        """Remove excessive newlines, tabs, and spaces."""
        if not text:
            return None
        cleaned = re.sub(r"\s+", " ", text).strip()
        return cleaned or None

    def _parse_feed(self, xml_content: str) -> List[PaperSchema]:
        """Parse Atom feed from arXiv into standardized PaperSchema objects."""
        results: List[PaperSchema] = []

        if feedparser is not None:
            feed = feedparser.parse(xml_content)
            for entry in feed.entries:
                paper = self._entry_to_schema(entry)
                if paper:
                    results.append(paper)
        else:
            # Fallback simple XML parse if feedparser is not present
            results = self._fallback_parse_xml(xml_content)

        return results

    def _entry_to_schema(self, entry: dict) -> Optional[PaperSchema]:
        """Convert a single feedparser entry to PaperSchema."""
        raw_id = entry.get("id", "")
        if not raw_id:
            return None

        # Extract clean arXiv identifier (e.g. "2301.12345v1" or "abs/2301.12345")
        arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id

        title = self._clean_text(entry.get("title", ""))
        if not title:
            return None

        # Authors
        authors: List[AuthorSchema] = []
        for author in entry.get("authors", []):
            name = self._clean_text(author.get("name", ""))
            if name:
                authors.append(
                    AuthorSchema(
                        name=name,
                        author_id=None,
                        affiliations=[],
                    )
                )

        # Publication Year
        year = None
        published = entry.get("published", "") or entry.get("updated", "")
        if published and len(published) >= 4:
            try:
                year = int(published[:4])
            except (ValueError, TypeError):
                year = None

        # Abstract / Summary
        abstract = self._clean_text(entry.get("summary", ""))

        # DOI
        doi = entry.get("arxiv_doi") or entry.get("doi")
        if doi:
            doi = str(doi).strip()
            if doi.lower().startswith("https://doi.org/"):
                doi = doi[16:]
            elif doi.lower().startswith("doi:"):
                doi = doi[4:]

        # Venue / Category
        primary_category = entry.get("arxiv_primary_category", {}).get("term")
        venue = f"arXiv ({primary_category})" if primary_category else "arXiv preprint"

        # URL
        url = entry.get("link") or f"https://arxiv.org/abs/{arxiv_id}"

        return PaperSchema(
            id=f"arxiv_{arxiv_id}",
            source=PaperSource.ARXIV,
            external_id=arxiv_id,
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            abstract=abstract,
            doi=doi,
            url=url,
            citation_count=0,
        )

    def _fallback_parse_xml(self, xml_content: str) -> List[PaperSchema]:
        """Fallback XML parser using standard library xml.etree.ElementTree."""
        import xml.etree.ElementTree as ET

        results: List[PaperSchema] = []
        try:
            root = ET.fromstring(xml_content)
            # Atom XML namespace
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

            for entry in root.findall("atom:entry", ns):
                id_elem = entry.find("atom:id", ns)
                title_elem = entry.find("atom:title", ns)
                if id_elem is None or title_elem is None:
                    continue

                raw_id = id_elem.text or ""
                arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id
                title = self._clean_text(title_elem.text)
                if not title:
                    continue

                authors: List[AuthorSchema] = []
                for author_elem in entry.findall("atom:author", ns):
                    name_elem = author_elem.find("atom:name", ns)
                    if name_elem is not None and name_elem.text:
                        authors.append(AuthorSchema(name=self._clean_text(name_elem.text) or "", author_id=None))

                published_elem = entry.find("atom:published", ns)
                year = None
                if published_elem is not None and published_elem.text and len(published_elem.text) >= 4:
                    try:
                        year = int(published_elem.text[:4])
                    except (ValueError, TypeError):
                        year = None

                summary_elem = entry.find("atom:summary", ns)
                abstract = self._clean_text(summary_elem.text) if summary_elem is not None else None

                doi_elem = entry.find("arxiv:doi", ns)
                doi = self._clean_text(doi_elem.text) if doi_elem is not None else None

                results.append(
                    PaperSchema(
                        id=f"arxiv_{arxiv_id}",
                        source=PaperSource.ARXIV,
                        external_id=arxiv_id,
                        title=title,
                        authors=authors,
                        year=year,
                        venue="arXiv preprint",
                        abstract=abstract,
                        doi=doi,
                        url=f"https://arxiv.org/abs/{arxiv_id}",
                        citation_count=0,
                    )
                )
        except Exception as e:
            logger.error(f"Fallback XML parsing failed: {e}", exc_info=True)

        return results


arxiv_service = ArxivService()
