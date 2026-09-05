from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

try:
    from backend.database import Base
except ImportError:
    from database import Base

import sys
import uuid

if "backend.models.draft_document" in sys.modules and __name__ == "models.draft_document":
    DraftDocument = sys.modules["backend.models.draft_document"].DraftDocument
elif "models.draft_document" in sys.modules and __name__ == "backend.models.draft_document":
    DraftDocument = sys.modules["models.draft_document"].DraftDocument
else:
    class DraftDocument(Base):
        __tablename__ = "draft_documents"
        __table_args__ = {"extend_existing": True}

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

        project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
        content = Column(JSON, nullable=False)
        chapter_ref = Column(String, nullable=True)
        word_count = Column(Integer, default=0)
        version = Column(Integer, default=1)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        updated_at = Column(DateTime(timezone=True), onupdate=func.now())

        project = relationship("Project", back_populates="draft_documents")


