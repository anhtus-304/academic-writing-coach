import sys
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

try:
    from backend.database import Base
except ImportError:
    from database import Base

import uuid

if "backend.models.project" in sys.modules and __name__ == "models.project":
    Project = sys.modules["backend.models.project"].Project
elif "models.project" in sys.modules and __name__ == "backend.models.project":
    Project = sys.modules["models.project"].Project
else:
    class Project(Base):
        __tablename__ = "projects"
        __table_args__ = {"extend_existing": True}

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

        user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
        topic = Column(String, nullable=False)
        document_type = Column(Enum("tieu_luan", "khoa_luan", "luan_van", name="document_type_enum"), nullable=False, default="tieu_luan")
        field = Column(String, nullable=True)
        university = Column(String, nullable=True)
        citation_style = Column(Enum("apa7", "ieee", "bgddt", name="citation_style_enum"), default="apa7")
        additional_requirements = Column(Text, nullable=True)
        status = Column(Enum("draft", "in_progress", "completed", name="project_status_enum"), default="draft", index=True)
        created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
        updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=func.now())

        owner = relationship("User", back_populates="projects")
        outlines = relationship("Outline", back_populates="project", cascade="all, delete-orphan")
        search_sessions = relationship("SearchSession", back_populates="project", cascade="all, delete-orphan")
        selected_papers = relationship("SelectedPaper", back_populates="project", cascade="all, delete-orphan")
        draft_documents = relationship("DraftDocument", back_populates="project", cascade="all, delete-orphan")



