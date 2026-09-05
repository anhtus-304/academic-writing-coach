from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

try:
    from backend.database import Base
except ImportError:
    from database import Base

import sys
import uuid

if "backend.models.search_session" in sys.modules and __name__ == "models.search_session":
    SearchSession = sys.modules["backend.models.search_session"].SearchSession
elif "models.search_session" in sys.modules and __name__ == "backend.models.search_session":
    SearchSession = sys.modules["models.search_session"].SearchSession
else:
    class SearchSession(Base):
        __tablename__ = "search_sessions"
        __table_args__ = {"extend_existing": True}

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

        project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
        query = Column(String, nullable=False)
        filters = Column(JSON, nullable=True)
        total_results = Column(Integer, default=0)
        expires_at = Column(DateTime(timezone=True), nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())

        project = relationship("Project", back_populates="search_sessions")
        cached_papers = relationship("CachedPaper", back_populates="session", cascade="all, delete-orphan")
