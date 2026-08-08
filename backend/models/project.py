import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    topic: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    field: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    document_type: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    language: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    citation_style: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    current_step: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    status: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    last_activity: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
    user = relationship(
        "User",
        back_populates="projects",
    )

    outlines = relationship(
        "Outline",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    search_sessions = relationship(
        "SearchSession",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    draft_documents = relationship(
        "DraftDocument",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    ai_use_logs = relationship(
        "AILog",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    selected_papers = relationship(
        "SelectedPaper",
        back_populates="project",
        cascade="all, delete-orphan",
    )