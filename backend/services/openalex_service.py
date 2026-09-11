import logging
from typing import Dict, List, Optional
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


class OpenAlexService:
    """Client for querying academic literature from the OpenAlex Works API."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        email: Optional[str] = None,
        timeout: float = 12.0,
    ):
        self.api_url = api_url or settings.OPENALEX_WORKS_URL
        self.email = email or settings.OPENALEX_MAILTO
        self.timeout = timeout

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> List[PaperSchema]:
        """Search papers from OpenAlex matching the given query."""
        if not query or not query.strip():
            return []

        params = {
            "search": query.strip(),
            "per_page": min(max(1, limit), 50),
            "sort": "relevance_score:desc",
        }
        if self.email:
            params["mailto"] = self.email

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
                        f"OpenAlex API returned status {response.status_code}: {response.text[:200]}"
                    )
                    return []

                data = response.json()
                raw_results = data.get("results", [])
                return self._parse_results(raw_results)

        except httpx.TimeoutException:
            logger.warning(f"OpenAlex API timed out after {self.timeout}s for query: '{query}'")
            return []
        except Exception as e:
            logger.error(f"OpenAlex search error: {e}", exc_info=True)
            return []

    def _reconstruct_abstract(self, inverted_index: Optional[Dict[str, List[int]]]) -> Optional[str]:
        """Reconstruct full text abstract from OpenAlex inverted index format: {word: [pos1, pos2]}."""
        if not inverted_index or not isinstance(inverted_index, dict):
            return None

        word_pos_list = []
        for word, positions in inverted_index.items():
            if isinstance(positions, list):
                for pos in positions:
                    word_pos_list.append((pos, word))

        if not word_pos_list:
            return None

        # Sort by position index
        word_pos_list.sort(key=lambda x: x[0])
        abstract_text = " ".join(word for _, word in word_pos_list)
        return abstract_text.strip() or None

    def _parse_results(self, raw_results: List[dict]) -> List[PaperSchema]:
        """Parse OpenAlex work objects into standardized PaperSchema."""
        results: List[PaperSchema] = []

        for item in raw_results:
            work_id = item.get("id") or ""
            # Clean OpenAlex ID (e.g., https://openalex.org/W2741809807 -> W2741809807)
            external_id = work_id.split("/")[-1] if "/" in work_id else work_id
            if not external_id:
                continue

            title = (item.get("title") or item.get("display_name") or "").strip()
            if not title:
                continue

            # Authors and Affiliations
            authors: List[AuthorSchema] = []
            for authorship in item.get("authorships", []):
                author_obj = authorship.get("author") or {}
                author_name = author_obj.get("display_name")
                if author_name:
                    author_id = author_obj.get("id", "").split("/")[-1] if author_obj.get("id") else None
                    affiliations = [
                        inst.get("display_name")
                        for inst in authorship.get("institutions", [])
                        if inst.get("display_name")
                    ]
                    authors.append(
                        AuthorSchema(
                            name=author_name.strip(),
                            author_id=author_id,
                            affiliations=affiliations,
                        )
                    )

            # DOI
            raw_doi = item.get("doi")
            doi = None
            if raw_doi:
                doi = str(raw_doi).strip()
                if doi.lower().startswith("https://doi.org/"):
                    doi = doi[16:]
                elif doi.lower().startswith("http://doi.org/"):
                    doi = doi[15:]
                elif doi.lower().startswith("doi:"):
                    doi = doi[4:]

            # Year
            year = item.get("publication_year")
            if year is not None:
                try:
                    year = int(year)
                except (ValueError, TypeError):
                    year = None

            # Venue / Host Source
            venue = None
            primary_loc = item.get("primary_location") or {}
            source_info = primary_loc.get("source") or {}
            if source_info and source_info.get("display_name"):
                venue = source_info.get("display_name").strip()
            elif item.get("host_venue", {}).get("display_name"):
                venue = item["host_venue"]["display_name"].strip()

            # Abstract
            abstract = self._reconstruct_abstract(item.get("abstract_inverted_index"))

            # Citation count
            citation_count = item.get("cited_by_count") or 0
            try:
                citation_count = int(citation_count)
            except (ValueError, TypeError):
                citation_count = 0

            # URL
            url = primary_loc.get("landing_page_url") or (f"https://doi.org/{doi}" if doi else work_id)

            paper = PaperSchema(
                id=f"openalex_{external_id}",
                source=PaperSource.OPENALEX,
                external_id=external_id,
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


openalex_service = OpenAlexService()
