from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import uuid

class SelectedPaper(Base):
    __tablename__ = "selected_papers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    cached_paper_id = Column(String, ForeignKey("cached_papers.id"), nullable=False)
    relevant_sections = Column(JSON, nullable=True)
    citation_formatted = Column(Text, nullable=True)
    used_in_draft = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    selected_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="selected_papers")
    cached_paper = relationship("CachedPaper", back_populates="selected_papers")