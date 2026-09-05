from sqlalchemy import Column, String, Integer, DateTime, Float, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, synonym

try:
    from backend.database import Base
except ImportError:
    from database import Base

import sys
import uuid

if "backend.models.cached_paper" in sys.modules and __name__ == "models.cached_paper":
    CachedPaper = sys.modules["backend.models.cached_paper"].CachedPaper
elif "models.cached_paper" in sys.modules and __name__ == "backend.models.cached_paper":
    CachedPaper = sys.modules["models.cached_paper"].CachedPaper
else:
    class CachedPaper(Base):
        __tablename__ = "cached_papers"
        __table_args__ = {"extend_existing": True}

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

        search_session_id = synonym("session_id")
        publication_year = synonym("year")

        session = relationship("SearchSession", back_populates="cached_papers")
        selected_papers = relationship("SelectedPaper", back_populates="cached_paper", cascade="all, delete-orphan")
