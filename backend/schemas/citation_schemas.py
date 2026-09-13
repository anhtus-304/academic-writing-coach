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


class MissingCitationClaim(BaseModel):
    sentence: str
    reason: str
    suggested_action: str
    recommended_paper_id: Optional[str] = None
    recommended_paper_title: Optional[str] = None
    in_text_suggestion: Optional[str] = None


class UncitedPaperItem(BaseModel):
    id: Optional[str] = None
    title: str
    authors: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    in_text_code: Optional[str] = None  # e.g. "(Vaswani et al., 2017)" or "[1]"
    suggested_action: str = "Tài liệu này đã được chọn nhưng chưa được trích dẫn trong bài viết."


class CitationCheckResponse(BaseModel):
    total_issues: int
    missing_claims: List[MissingCitationClaim] = Field(default_factory=list)
    invalid_citations: List[str] = Field(default_factory=list)
    citation_warnings: List[str] = Field(default_factory=list)
    uncited_papers: List[UncitedPaperItem] = Field(default_factory=list)
    verified_count: int = 0
    credits_charged: int = 2


class ProjectBibliographyResponse(BaseModel):
    project_id: str
    style: CitationStyle
    total_references: int
    bibliography: List[str] = Field(default_factory=list)
    html_formatted: str = ""

