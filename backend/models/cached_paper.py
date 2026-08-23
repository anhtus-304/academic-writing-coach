<<<<<<< HEAD
from sqlalchemy import Column, String, Integer, DateTime, Float, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import uuid
=======
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

>>>>>>> d3103348d82d49a068dcb68ce6bf20e6b924f027

class CachedPaper(Base):
    __tablename__ = "cached_papers"

<<<<<<< HEAD
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
=======
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    authors: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    abstract: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    doi: Mapped[str | None] = mapped_column(
        String,
        unique=True,
        nullable=True,
    )

    url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    publication_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    citation_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    selected_papers = relationship(
        "SelectedPaper",
        back_populates="paper",
        cascade="all, delete-orphan",
    )
>>>>>>> d3103348d82d49a068dcb68ce6bf20e6b924f027
