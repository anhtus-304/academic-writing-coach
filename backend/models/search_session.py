from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import uuid

class SearchSession(Base):
    __tablename__ = "search_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    query = Column(String, nullable=False)
    filters = Column(JSON, nullable=True)
    total_results = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="search_sessions")
    cached_papers = relationship("CachedPaper", back_populates="session", cascade="all, delete-orphan")