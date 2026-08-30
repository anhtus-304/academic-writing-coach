import re
import math
import difflib
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Set

try:
    from schemas.literature_schemas import (
        PaperSchema,
        PaperSource,
        SearchResponseSchema,
    )
    from services.scholar_service import ScholarService, scholar_service
    from services.arxiv_service import ArxivService, arxiv_service
    from services.openalex_service import OpenAlexService, openalex_service
except ImportError:
    from backend.schemas.literature_schemas import (
        PaperSchema,
        PaperSource,
        SearchResponseSchema,
    )
    from backend.services.scholar_service import ScholarService, scholar_service
    from backend.services.arxiv_service import ArxivService, arxiv_service
    from backend.services.openalex_service import OpenAlexService, openalex_service

logger = logging.getLogger(__name__)

STOP_WORDS: Set[str] = {
    "a", "an", "the", "in", "on", "at", "for", "to", "of", "and", "or", "with",
    "by", "from", "as", "is", "are", "was", "were", "be", "been", "that", "which",
    "this", "these", "those", "using", "based", "via", "towards", "study", "research",
}


class SearchAggregator:
    """Aggregates search results from Semantic Scholar, arXiv, and OpenAlex,

    providing concurrent fetching, deduplication, and multi-factor ranking.
    """

    def __init__(
        self,
        scholar_client: Optional[ScholarService] = None,
        arxiv_client: Optional[ArxivService] = None,
        openalex_client: Optional[OpenAlexService] = None,
    ):
        self.scholar_client = scholar_client or scholar_service
        self.arxiv_client = arxiv_client or arxiv_service
        self.openalex_client = openalex_client or openalex_service

    async def aggregate_search(
        self,
        query: str,
        limit: int = 10,
        sources: Optional[List[PaperSource]] = None,
    ) -> SearchResponseSchema:
        """Search across selected academic API sources concurrently,

        deduplicate results, calculate ranking scores, and return sorted papers.
        """
        if not query or not query.strip():
            return SearchResponseSchema(query=query, total_results=0, papers=[])

        clean_query = query.strip()
        selected_sources = sources or [
            PaperSource.SEMANTIC_SCHOLAR,
            PaperSource.ARXIV,
            PaperSource.OPENALEX,
        ]

        # Dispatch async tasks concurrently
        tasks = []
        task_source_map = []

        if PaperSource.SEMANTIC_SCHOLAR in selected_sources:
            tasks.append(self.scholar_client.search(clean_query, limit=limit))
            task_source_map.append(PaperSource.SEMANTIC_SCHOLAR)

        if PaperSource.ARXIV in selected_sources:
            tasks.append(self.arxiv_client.search(clean_query, limit=limit))
            task_source_map.append(PaperSource.ARXIV)

        if PaperSource.OPENALEX in selected_sources:
            tasks.append(self.openalex_client.search(clean_query, limit=limit))
            task_source_map.append(PaperSource.OPENALEX)

        logger.info(
            f"Dispatching concurrent search across {len(tasks)} sources for: '{clean_query}'"
        )
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        all_papers: List[PaperSchema] = []
        for src, result in zip(task_source_map, task_results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching papers from {src}: {result}")
            elif isinstance(result, list):
                logger.info(f"Retrieved {len(result)} papers from {src}")
                all_papers.extend(result)

        # 1. Deduplicate papers across sources
        deduped_papers = self.deduplicate_papers(all_papers)
        logger.info(
            f"Deduplication complete: {len(all_papers)} raw -> {len(deduped_papers)} unique papers"
        )

        # 2. Multi-factor Ranking
        ranked_papers = self.rank_papers(deduped_papers, clean_query)

        # 3. Limit final results
        final_papers = ranked_papers[:limit] if limit > 0 else ranked_papers

        return SearchResponseSchema(
            query=clean_query,
            total_results=len(ranked_papers),
            papers=final_papers,
        )

    # -------------------------------------------------------------------------
    # Deduplication Logic
    # -------------------------------------------------------------------------

    @staticmethod
    def normalize_doi(doi: Optional[str]) -> Optional[str]:
        """Normalize DOI string by stripping URL prefixes, lowercase, and trimming."""
        if not doi:
            return None
        cleaned = str(doi).strip().lower()
        cleaned = re.sub(r"^https?:\/\/(?:dx\.)?doi\.org\/", "", cleaned)
        cleaned = re.sub(r"^doi:\s*", "", cleaned)
        return cleaned.strip() or None

    @staticmethod
    def normalize_title(title: Optional[str]) -> str:
        """Normalize paper title for fuzzy comparison."""
        if not title:
            return ""
        # Lowercase, strip punctuation and extra whitespace
        cleaned = re.sub(r"[^\w\s]", " ", title.lower())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def are_duplicates(self, paper1: PaperSchema, paper2: PaperSchema) -> bool:
        """Check whether two paper records refer to the same publication."""
        # 1. Check exact DOI match if both have DOI
        doi1 = self.normalize_doi(paper1.doi)
        doi2 = self.normalize_doi(paper2.doi)
        if doi1 and doi2 and doi1 == doi2:
            return True

        # 2. Check title similarity
        norm_t1 = self.normalize_title(paper1.title)
        norm_t2 = self.normalize_title(paper2.title)

        if not norm_t1 or not norm_t2:
            return False

        # Exact title match
        if norm_t1 == norm_t2:
            return True

        # SequenceMatcher similarity ratio
        ratio = difflib.SequenceMatcher(None, norm_t1, norm_t2).ratio()
        if ratio >= 0.88:
            # Check publication year compatibility if available
            if paper1.year and paper2.year and abs(paper1.year - paper2.year) > 1:
                return False
            return True

        # Jaccard word set similarity for long academic titles
        words1 = set(norm_t1.split()) - STOP_WORDS
        words2 = set(norm_t2.split()) - STOP_WORDS
        if words1 and words2:
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            jaccard = intersection / union if union > 0 else 0
            if jaccard >= 0.82:
                if paper1.year and paper2.year and abs(paper1.year - paper2.year) > 1:
                    return False
                return True

        return False

    def merge_paper_metadata(self, base: PaperSchema, incoming: PaperSchema) -> PaperSchema:
        """Merge metadata from two duplicate paper records to form the most complete record."""
        # Citation count: keep highest
        citation_count = max(base.citation_count or 0, incoming.citation_count or 0)

        # Abstract: keep longer and cleaner
        abstract = base.abstract
        if not abstract or (incoming.abstract and len(incoming.abstract) > len(abstract)):
            abstract = incoming.abstract

        # DOI: keep valid DOI
        doi = base.doi or incoming.doi

        # Venue: prefer non-preprint or longer description
        venue = base.venue
        if not venue or (incoming.venue and "preprint" not in incoming.venue.lower()):
            venue = incoming.venue or base.venue

        # Year: prefer non-None
        year = base.year or incoming.year

        # URL: prefer DOI link or non-empty
        url = base.url
        if doi and (not url or "arxiv" in (url or "") and "doi.org" in (incoming.url or "")):
            url = incoming.url or base.url
        elif not url:
            url = incoming.url

        # Authors: prefer longer list or list with affiliations
        authors = base.authors
        if not authors:
            authors = incoming.authors
        elif incoming.authors:
            if len(incoming.authors) > len(authors):
                authors = incoming.authors
            elif any(a.affiliations for a in incoming.authors) and not any(a.affiliations for a in authors):
                authors = incoming.authors

        return PaperSchema(
            id=base.id,
            source=base.source,
            external_id=base.external_id,
            title=base.title if len(base.title) >= len(incoming.title) else incoming.title,
            authors=authors,
            year=year,
            venue=venue,
            abstract=abstract,
            doi=doi,
            url=url,
            citation_count=citation_count,
            summary_vi=base.summary_vi or incoming.summary_vi,
            relevance_score=base.relevance_score,
        )

    def deduplicate_papers(self, papers: List[PaperSchema]) -> List[PaperSchema]:
        """Group and deduplicate a list of papers from multiple sources."""
        unique_papers: List[PaperSchema] = []

        for paper in papers:
            matched_idx = -1
            for idx, existing in enumerate(unique_papers):
                if self.are_duplicates(existing, paper):
                    matched_idx = idx
                    break

            if matched_idx != -1:
                # Merge into existing entry
                unique_papers[matched_idx] = self.merge_paper_metadata(
                    unique_papers[matched_idx], paper
                )
            else:
                unique_papers.append(paper)

        return unique_papers

    # -------------------------------------------------------------------------
    # Multi-factor Ranking Algorithm
    # -------------------------------------------------------------------------

    def calculate_ranking_score(
        self, paper: PaperSchema, query_tokens: List[str], raw_query: str, current_year: int
    ) -> float:
        """Compute multi-factor relevance score between 0.0 and 1.0.

        Factors:
        - 55% Keyword match in Title & Abstract
        - 20% Recency Boost (papers published in recent years)
        - 25% Citation Authority Boost (log scale)
        """
        # 1. Text match score
        norm_title = self.normalize_title(paper.title)
        norm_abstract = self.normalize_title(paper.abstract or "")
        norm_query = self.normalize_title(raw_query)

        title_words = set(norm_title.split())
        abstract_words = set(norm_abstract.split())

        title_overlap = 0.0
        abstract_overlap = 0.0

        if query_tokens:
            title_matches = sum(1 for token in query_tokens if token in title_words)
            title_overlap = title_matches / len(query_tokens)

            abstract_matches = sum(1 for token in query_tokens if token in abstract_words)
            abstract_overlap = abstract_matches / len(query_tokens)

        # Exact phrase match bonus in title
        exact_phrase_bonus = 0.2 if norm_query and norm_query in norm_title else 0.0

        text_score = min(1.0, (title_overlap * 0.65) + (abstract_overlap * 0.25) + exact_phrase_bonus)

        # 2. Recency boost score
        paper_year = paper.year or (current_year - 5)
        year_diff = max(0, current_year - paper_year)
        if year_diff <= 2:
            recency_score = 1.0
        elif year_diff <= 5:
            recency_score = 0.85
        elif year_diff <= 10:
            recency_score = 0.65
        else:
            recency_score = max(0.2, 0.65 - (year_diff - 10) * 0.03)

        # 3. Citation authority score (logarithmic scale)
        citations = paper.citation_count or 0
        if citations > 0:
            # log10(1) = 0, log10(10)=1 -> 0.25, log10(100)=2 -> 0.5, log10(10000)=4 -> 1.0
            citation_score = min(1.0, math.log10(1 + citations) / 4.0)
        else:
            citation_score = 0.1

        # Composite score
        total_score = (text_score * 0.55) + (recency_score * 0.20) + (citation_score * 0.25)
        # Clamped to range [0.05, 1.00]
        final_score = round(max(0.05, min(1.0, total_score)), 3)
        return final_score

    def rank_papers(self, papers: List[PaperSchema], query: str) -> List[PaperSchema]:
        """Score each paper and sort in descending order of relevance score."""
        current_year = datetime.now(timezone.utc).year
        clean_query = self.normalize_title(query)
        raw_tokens = clean_query.split()
        query_tokens = [t for t in raw_tokens if t not in STOP_WORDS and len(t) > 1]
        if not query_tokens:
            query_tokens = raw_tokens

        ranked_list: List[PaperSchema] = []
        for paper in papers:
            score = self.calculate_ranking_score(paper, query_tokens, query, current_year)
            # Create a copy with updated relevance score
            scored_paper = paper.model_copy(update={"relevance_score": score})
            ranked_list.append(scored_paper)

        # Sort descending by relevance score, then citation count, then year
        ranked_list.sort(
            key=lambda p: (
                p.relevance_score or 0.0,
                p.citation_count or 0,
                p.year or 0,
            ),
            reverse=True,
        )

        return ranked_list


search_aggregator = SearchAggregator()
