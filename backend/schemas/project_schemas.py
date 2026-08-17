from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    tieu_luan = "tieu_luan"
    khoa_luan = "khoa_luan"
    luan_van = "luan_van"

class CitationStyle(str, Enum):
    apa7 = "apa7"
    ieee = "ieee"
    bgddt = "bgddt"

class ProjectBase(BaseModel):
    topic: str
    document_type: DocumentType = DocumentType.tieu_luan
    field: Optional[str] = None
    university: Optional[str] = None
    citation_style: CitationStyle = CitationStyle.apa7
    additional_requirements: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    topic: Optional[str] = None
    document_type: Optional[DocumentType] = None
    field: Optional[str] = None
    university: Optional[str] = None
    citation_style: Optional[CitationStyle] = None
    additional_requirements: Optional[str] = None
    status: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: str
    user_id: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True