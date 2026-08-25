from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import uuid

class Outline(Base):
    __tablename__ = "outlines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, unique=True)
    title = Column(String, nullable=True)
    chapters = Column(JSON, nullable=False)
    suggestions = Column(JSON, nullable=True)
    template_source = Column(String, nullable=True)
    version = Column(Integer, default=1)
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=func.now())

    project = relationship("Project", back_populates="outlines")