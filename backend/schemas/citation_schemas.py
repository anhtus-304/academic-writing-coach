from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class CitationStyle(str, Enum):
    APA7 = "apa7"
    IEEE = "ieee"
    BGDDT = "bgddt"


class DocumentType(str, Enum):
    JOURNAL = "journal"
    BOOK = "book"
    CONFERENCE = "conference"
    THESIS = "thesis"
    WEB = "web"


class CitationMetadataSchema(BaseModel):
    title: str = Field(..., description="Title of the work")
    authors: List[str] = Field(..., description="List of author full names, e.g., ['Nguyễn Văn A', 'Smith, John']")
    year: int = Field(..., description="Publication year")
    journal: Optional[str] = Field(None, description="Journal or publication venue name")
    volume: Optional[str] = Field(None, description="Volume number")
    issue: Optional[str] = Field(None, description="Issue number")
    pages: Optional[str] = Field(None, description="Page range, e.g., '45-52'")
    doi: Optional[str] = Field(None, description="DOI link or identifier")
    publisher: Optional[str] = Field(None, description="Publisher name or university")
    url: Optional[str] = Field(None, description="URL of the paper")
    doc_type: DocumentType = Field(DocumentType.JOURNAL, description="Type of document")


class FormatCitationRequest(BaseModel):
    metadata: CitationMetadataSchema = Field(..., description="Metadata of the source")
    style: CitationStyle = Field(CitationStyle.APA7, description="Desired citation style")
    index: int = Field(1, ge=1, description="Numerical index for numbered citation styles (e.g., IEEE/Bộ GD&ĐT)")


class FormatCitationResponse(BaseModel):
    in_text_citation: str = Field(..., description="Formatted in-text citation string")
    full_citation: str = Field(..., description="Formatted full bibliography entry")
    style: CitationStyle = Field(..., description="Citation style used")


class BibliographyRequest(BaseModel):
    metadatas: List[CitationMetadataSchema] = Field(..., description="List of paper metadatas")
    style: CitationStyle = Field(CitationStyle.APA7, description="Desired citation style")


class BibliographyResponse(BaseModel):
    citations: List[str] = Field(..., description="Formatted & sorted list of bibliography entries")
    style: CitationStyle = Field(..., description="Citation style used")


class CitationCheckRequest(BaseModel):
    content: str = Field(..., min_length=10, description="Draft text or HTML content to analyze")
    citation_style: Optional[str] = Field("apa7", description="Citation style: apa7, ieee, bgddt")
    paper_ids: Optional[List[str]] = Field(
        None,
        description=(
            "Danh sách SelectedPaper.id dùng làm danh mục đối chiếu cho lần kiểm tra này. "
            "Bỏ trống/None = dùng toàn bộ tài liệu đã chọn của project."
        ),
    )


class MissingCitationClaim(BaseModel):
    sentence: str
    reason: str
    suggested_action: str
    recommended_paper_id: Optional[str] = None
    recommended_paper_title: Optional[str] = None
    in_text_suggestion: Optional[str] = None

    # --- Position metadata (used by the Tiptap editor to highlight the claim) ---
    sentence_index: Optional[int] = Field(
        None, description="Thứ tự của câu trong toàn văn (bắt đầu từ 0)"
    )
    char_offset: Optional[int] = Field(
        None, description="Vị trí ký tự bắt đầu của câu trong văn bản thuần (plain text)"
    )
    char_end: Optional[int] = Field(
        None, description="Vị trí ký tự kết thúc (exclusive) của câu trong văn bản thuần"
    )


class UncitedPaperItem(BaseModel):
    id: Optional[str] = None
    title: str
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    in_text_code: Optional[str] = None  # e.g. "(Vaswani et al., 2017)" or "[1]"
    suggested_action: str = "Tài liệu này đã được chọn nhưng chưa được trích dẫn trong bài viết."


class MissingCitationSnippet(BaseModel):
    """Compact missing-citation item (week-3 API contract).

    Shape: ``{"text": <câu thiếu nguồn>, "index": <thứ tự câu>, "suggestion": <gợi ý>}``.
    """

    text: str = Field(..., description="Câu/nhận định đang thiếu nguồn")
    index: int = Field(0, ge=0, description="Thứ tự của câu trong toàn văn (bắt đầu từ 0)")
    suggestion: str = Field("", description="Gợi ý cách bổ sung nguồn cho câu này")


class CitationCheckResponse(BaseModel):
    total_issues: int
    missing_claims: List[MissingCitationClaim] = Field(default_factory=list)
    invalid_citations: List[str] = Field(default_factory=list)
    citation_warnings: List[str] = Field(default_factory=list)
    uncited_papers: List[UncitedPaperItem] = Field(default_factory=list)
    verified_count: int = 0
    credits_charged: int = 2

    # --- Compact contract required by the week-3 task ---
    missing: List[MissingCitationSnippet] = Field(
        default_factory=list,
        description="Dạng rút gọn [{text, index, suggestion}] của missing_claims",
    )
    total_missing: int = Field(0, ge=0, description="Tổng số câu/nhận định thiếu trích dẫn")


class ProjectBibliographyResponse(BaseModel):
    project_id: str
    style: CitationStyle
    total_references: int
    bibliography: List[str] = Field(default_factory=list)
    bibliography_text: str = Field(
        "", description="Danh mục tài liệu tham khảo dạng văn bản (mỗi entry 1 dòng)"
    )
    html_formatted: str = ""


class ProjectCitationFormatRequest(BaseModel):
    """Request body for POST /projects/{project_id}/citation/format."""

    style: Optional[CitationStyle] = Field(
        None, description="Citation style override; falls back to the project setting (apa7)"
    )
    selected_paper_ids: Optional[List[str]] = Field(
        None,
        description="Optional subset of SelectedPaper ids to format; omit to format every selected paper",
    )
    paper_ids: Optional[List[str]] = Field(
        None,
        description="Alias của selected_paper_ids (week-3 contract: [{paper_ids, style}])",
    )
    include_in_text: bool = Field(
        True, description="Include the per-paper in-text citation code in the response"
    )


class FormattedPaperCitation(BaseModel):
    selected_paper_id: Optional[str] = None
    paper_id: Optional[str] = None
    title: str
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    in_text_citation: str = ""
    full_citation: str = ""
    style: CitationStyle = CitationStyle.APA7


class ProjectCitationFormatResponse(BaseModel):
    project_id: str
    style: CitationStyle
    total_citations: int
    citations: List[FormattedPaperCitation] = Field(default_factory=list)
    bibliography: List[str] = Field(default_factory=list)
    bibliography_text: str = Field(
        "",
        description="Toàn bộ danh mục tài liệu tham khảo dạng văn bản (mỗi entry 1 dòng, ngăn cách '\\n')",
    )
    html_formatted: str = ""

