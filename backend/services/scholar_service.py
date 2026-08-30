import logging
from typing import List, Optional
import httpx

try:
    from schemas.literature_schemas import AuthorSchema, PaperSchema, PaperSource
except ImportError:
    from backend.schemas.literature_schemas import AuthorSchema, PaperSchema, PaperSource

try:
    from config import settings
except ImportError:
    from backend.config import settings

logger = logging.getLogger(__name__)

DEFAULT_FIELDS = "paperId,title,authors,year,venue,abstract,externalIds,url,citationCount,isOpenAccess"


class ScholarService:
    """Client for querying academic papers from the Semantic Scholar Graph API."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 12.0,
    ):
        self.api_url = api_url or settings.SEMANTIC_SCHOLAR_SEARCH_URL
        self.api_key = api_key or settings.SEMANTIC_SCHOLAR_API_KEY
        self.timeout = timeout

    async def search(
        self,
        query: str,
        limit: int = 10,
        fields: Optional[str] = None,
    ) -> List[PaperSchema]:
        """Search papers from Semantic Scholar matching the given query."""
        if not query or not query.strip():
            return []

        headers = {
            "User-Agent": "AcademicWritingCoach/1.0 (academic-research-tool)",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key

        params = {
            "query": query.strip(),
            "limit": min(max(1, limit), 100),
            "fields": fields or DEFAULT_FIELDS,
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
                        f"Semantic Scholar API returned status {response.status_code}: {response.text[:200]}"
                    )
                    return []

                data = response.json()
                raw_papers = data.get("data", [])
                return self._parse_papers(raw_papers)

        except httpx.TimeoutException:
            logger.warning(f"Semantic Scholar API timed out after {self.timeout}s for query: '{query}'")
            return []
        except Exception as e:
            logger.error(f"Semantic Scholar search error: {e}", exc_info=True)
            return []

    def _parse_papers(self, raw_papers: List[dict]) -> List[PaperSchema]:
        """Parse raw Semantic Scholar response items into standardized PaperSchema objects."""
        results: List[PaperSchema] = []

        for item in raw_papers:
            paper_id = item.get("paperId")
            if not paper_id:
                continue

            title = (item.get("title") or "").strip()
            if not title:
                continue

            # Authors
            authors: List[AuthorSchema] = []
            for author in item.get("authors", []):
                author_name = author.get("name")
                if author_name:
                    authors.append(
                        AuthorSchema(
                            name=author_name.strip(),
                            author_id=author.get("authorId"),
                            affiliations=[],
                        )
                    )

            # DOI extraction
            external_ids = item.get("externalIds") or {}
            doi = external_ids.get("DOI") or external_ids.get("doi")
            if doi:
                doi = str(doi).strip()
                if doi.lower().startswith("https://doi.org/"):
                    doi = doi[16:]
                elif doi.lower().startswith("doi:"):
                    doi = doi[4:]

            # Year
            year = item.get("year")
            if year is not None:
                try:
                    year = int(year)
                except (ValueError, TypeError):
                    year = None

            # Venue
            venue = item.get("venue")
            if venue:
                venue = str(venue).strip() or None

            # Abstract
            abstract = item.get("abstract")
            if abstract:
                abstract = str(abstract).strip() or None

            # URL
            url = item.get("url") or (f"https://doi.org/{doi}" if doi else f"https://www.semanticscholar.org/paper/{paper_id}")

            # Citation count
            citation_count = item.get("citationCount") or 0
            try:
                citation_count = int(citation_count)
            except (ValueError, TypeError):
                citation_count = 0

            paper = PaperSchema(
                id=f"s2_{paper_id}",
                source=PaperSource.SEMANTIC_SCHOLAR,
                external_id=paper_id,
                title=title,
                authors=authors,
                year=year,
                venue=venue,
                abstract=abstract,
                doi=doi,
                url=url,
                citation_count=citation_count,
            )
            results.append(paper)

        return results


scholar_service = ScholarService()
