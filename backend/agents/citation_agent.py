import re
from typing import Any, Dict, List, Optional

try:
    from backend.agents.base_agent import BaseAgent
    from backend.schemas.citation_schemas import CitationMetadataSchema, CitationStyle, DocumentType
    from backend.services.citation_formatter import CitationFormatterService
except ImportError:
    from agents.base_agent import BaseAgent
    from schemas.citation_schemas import CitationMetadataSchema, CitationStyle, DocumentType
    from services.citation_formatter import CitationFormatterService


CLAIM_INDICATORS = [
    r"\b\d+[\.,]?\d*%",
    r"\bchiếm\s+\d+",
    r"\btăng\s+\d+",
    r"\bgiảm\s+\d+",
    r"\btheo\s+nghiên cứu\b",
    r"\bcác\s+nghiên cứu\s+chỉ ra\b",
    r"\btheo\s+báo cáo\b",
    r"\bthống kê\s+cho thấy\b",
    r"\bkết quả\s+cho thấy\b",
    r"\bđược\s+chứng minh\s+là\b",
    r"\bkhảo sát\s+tại\b",
]

CITATION_PATTERNS = [
    r"\[\d+\]",
    r"\([A-ZÀ-Ỹa-zà-ỹ][^()\n,]{0,80},\s*\d{4}\)",
    r"\([A-ZÀ-Ỹa-zà-ỹ][^()\n]{0,80}\bet\s+al\.,\s*\d{4}\)",
]


def clean_html_to_text(content: str) -> str:
    text = re.sub(r"<[^>]+>", " ", content or "")
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> List[str]:
    return [sentence.strip() for sentence in re.split(r"(?<=[.?!])\s+", text) if len(sentence.strip()) > 15]


def _as_metadata(paper: Dict[str, Any]) -> Optional[CitationMetadataSchema]:
    source = paper.get("paper", paper)
    authors = source.get("authors") or []
    if isinstance(authors, str):
        authors = [author.strip() for author in authors.split(",") if author.strip()]
    if not source.get("title") or not source.get("year") or not authors:
        return None
    doc_type = source.get("doc_type", source.get("document_type", "journal"))
    try:
        return CitationMetadataSchema(
            title=source["title"],
            authors=authors,
            year=int(source["year"]),
            journal=source.get("journal") or source.get("publicationType"),
            volume=source.get("volume"),
            issue=source.get("issue"),
            pages=source.get("pages"),
            doi=source.get("doi"),
            publisher=source.get("publisher"),
            url=source.get("url"),
            doc_type=doc_type if doc_type in {item.value for item in DocumentType} else DocumentType.JOURNAL,
        )
    except (TypeError, ValueError):
        return None


def _author_surnames(metadata: CitationMetadataSchema) -> List[str]:
    surnames = []
    for author in metadata.authors:
        parts = author.strip().split(",")
        surname = parts[0] if len(parts) > 1 else author.strip().split()[-1]
        if surname:
            surnames.append(surname.lower())
    return surnames


class CitationAgent(BaseAgent):
    """Analyzes claims and validates citations against selected paper metadata."""

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        content = clean_html_to_text(input_data.get("content", input_data.get("document", "")))
        style_value = input_data.get("citation_style", CitationStyle.APA7.value)
        try:
            style = CitationStyle(style_value)
        except ValueError:
            style = CitationStyle.APA7

        metadata = [
            item for paper in input_data.get("selected_papers", input_data.get("papers", []))
            if (item := _as_metadata(paper)) is not None
        ]
        sentences = split_sentences(content)
        citation_regex = re.compile("|".join(CITATION_PATTERNS))
        missing_claims: List[Dict[str, str]] = []
        suggestions: List[Dict[str, Any]] = []

        for sentence in sentences:
            if citation_regex.search(sentence):
                continue
            reason = next(
                ("Claim contains statistical evidence but no citation." for indicator in CLAIM_INDICATORS if re.search(indicator, sentence, re.IGNORECASE)),
                None,
            )
            if reason is None:
                continue
            issue = {
                "sentence": sentence,
                "reason": reason,
                "suggested_action": "Add a supporting citation.",
            }
            missing_claims.append(issue)
            suggestion: Dict[str, Any] = {
                "original_text": sentence,
                "reason": reason,
                "source": None,
                "suggested_text": None,
            }
            if metadata:
                formatted = CitationFormatterService.format_citation(metadata[0], style=style, index=1)
                suggestion.update({
                    "suggested_text": f"{sentence} {formatted.in_text_citation}",
                    "source": metadata[0].model_dump(),
                })
            else:
                suggestion["reason"] = f"{reason} No selected paper is available; add a source without inventing one."
            suggestions.append(suggestion)

        invalid_citations: List[str] = []
        verified_count = 0
        known_surnames = {surname for item in metadata for surname in _author_surnames(item)}
        citations = citation_regex.findall(content)
        for citation in citations:
            numeric = re.fullmatch(r"\[(\d+)\]", citation)
            if numeric:
                index = int(numeric.group(1))
                if index <= len(metadata):
                    verified_count += 1
                else:
                    invalid_citations.append(f"Citation {citation} is not present in the selected bibliography.")
                continue
            author_match = re.match(r"\(([^,()]+?)(?:\s+et\s+al\.)?,\s*(\d{4})\)", citation)
            if author_match and any(surname in author_match.group(1).lower() for surname in known_surnames):
                verified_count += 1
            elif author_match:
                invalid_citations.append(f"Author in '{citation}' is not present in the selected bibliography.")

        bibliography = CitationFormatterService.format_bibliography(metadata, style=style).citations
        return {
            "citation_issues": missing_claims + [{"citation": item} for item in invalid_citations],
            "missing_claims": missing_claims,
            "invalid_citations": invalid_citations,
            "suggestions": suggestions,
            "bibliography": bibliography,
            "citation_metadata": [item.model_dump() for item in metadata],
            "verified_count": verified_count,
        }


citation_agent = CitationAgent()
