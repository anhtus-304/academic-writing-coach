<<<<<<< HEAD
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import uuid
=======
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

>>>>>>> d3103348d82d49a068dcb68ce6bf20e6b924f027

class SelectedPaper(Base):
    __tablename__ = "selected_papers"

<<<<<<< HEAD
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
=======
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id"),
        nullable=False,
    )

    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cached_papers.id"),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    project = relationship(
        "Project",
        back_populates="selected_papers",
    )

    paper = relationship(
        "CachedPaper",
        back_populates="selected_papers",
    )
>>>>>>> d3103348d82d49a068dcb68ce6bf20e6b924f027
