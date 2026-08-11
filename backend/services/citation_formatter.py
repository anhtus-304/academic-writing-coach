from typing import List
from schemas.citation_schemas import (
    CitationMetadataSchema,
    CitationStyle,
    FormatCitationResponse,
    BibliographyResponse,
)
from data.citation_styles.apa7 import format_apa7_full, format_apa7_in_text
from data.citation_styles.ieee import format_ieee_full, format_ieee_in_text
from data.citation_styles.bgddt import (
    format_bgddt_full,
    format_bgddt_in_text,
    sort_bgddt_bibliography,
)


class CitationFormatterService:
    """
    Rule-based Citation Formatter Engine supporting APA 7th, IEEE, and Vietnamese Bộ GD&ĐT styles.
    Does not rely on LLM to ensure 100% precision and sub-millisecond execution time.
    """

    @staticmethod
    def format_citation(
        metadata: CitationMetadataSchema,
        style: CitationStyle = CitationStyle.APA7,
        index: int = 1,
    ) -> FormatCitationResponse:
        """
        Formats a single citation metadata into in-text and full bibliography entry.
        """
        if style == CitationStyle.APA7:
            in_text = format_apa7_in_text(metadata)
            full = format_apa7_full(metadata)
        elif style == CitationStyle.IEEE:
            in_text = format_ieee_in_text(index)
            full = format_ieee_full(metadata, index=index)
        elif style == CitationStyle.BGDDT:
            in_text = format_bgddt_in_text(metadata, index=index, use_numeric=True)
            full = format_bgddt_full(metadata, index=index)
        else:
            # Default fallback to APA7
            in_text = format_apa7_in_text(metadata)
            full = format_apa7_full(metadata)

        return FormatCitationResponse(
            in_text_citation=in_text,
            full_citation=full,
            style=style,
        )

    @staticmethod
    def format_bibliography(
        metadatas: List[CitationMetadataSchema],
        style: CitationStyle = CitationStyle.APA7,
    ) -> BibliographyResponse:
        """
        Formats a list of citation metadatas into a sorted bibliography list.
        """
        if not metadatas:
            return BibliographyResponse(citations=[], style=style)

        if style == CitationStyle.APA7:
            # Sorted alphabetically by first author surname
            sorted_meta = sorted(
                metadatas,
                key=lambda m: m.authors[0].lower() if m.authors else "unknown"
            )
            citations = [format_apa7_full(m) for m in sorted_meta]

        elif style == CitationStyle.IEEE:
            # Numbered in order of appearance (index 1..N)
            citations = [format_ieee_full(m, index=i + 1) for i, m in enumerate(metadatas)]

        elif style == CitationStyle.BGDDT:
            # Sorted by Bộ GD&ĐT rules: VN items (by Given Name) then Foreign items (by Surname)
            sorted_meta = sort_bgddt_bibliography(metadatas)
            citations = [format_bgddt_full(m, index=i + 1) for i, m in enumerate(sorted_meta)]

        else:
            citations = [format_apa7_full(m) for m in metadatas]

        return BibliographyResponse(
            citations=citations,
            style=style,
        )
