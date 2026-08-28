from sqlalchemy import Column, String, Integer, DateTime, Float, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import uuid

class CachedPaper(Base):
    __tablename__ = "cached_papers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("search_sessions.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    authors = Column(JSON, nullable=True)
    year = Column(Integer, nullable=True)
    source = Column(String, nullable=True)
    doi = Column(String, nullable=True, index=True)
    url = Column(String, nullable=True)
    abstract = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    citation_count = Column(Integer, default=0)
    relevance_score = Column(Float, default=0.0)
    raw_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("SearchSession", back_populates="cached_papers")
    selected_papers = relationship("SelectedPaper", back_populates="cached_paper", cascade="all, delete-orphan")