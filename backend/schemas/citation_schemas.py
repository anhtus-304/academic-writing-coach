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
