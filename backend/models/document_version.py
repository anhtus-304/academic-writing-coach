import sys
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func

try:
    from backend.database import Base
except ImportError:
    from database import Base

if "backend.models.document_version" in sys.modules and __name__ == "models.document_version":
    DocumentVersion = sys.modules["backend.models.document_version"].DocumentVersion
elif "models.document_version" in sys.modules and __name__ == "backend.models.document_version":
    DocumentVersion = sys.modules["models.document_version"].DocumentVersion
else:
    class DocumentVersion(Base):
        """Immutable snapshot of a document at a specific version.

        Used for conflict detection (content_hash), undo/rollback
        (version chain), and audit trail (source_job_id, created_by).
        """
        __tablename__ = "document_versions"
        __table_args__ = {"extend_existing": True}

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)

        version = Column(Integer, nullable=False)
        content = Column(JSON, nullable=False)
        content_hash = Column(String, nullable=False)  # SHA-256 hex digest
        word_count = Column(Integer, default=0)

        source_job_id = Column(String, ForeignKey("agent_jobs.id"), nullable=True)
        source_proposal_id = Column(String, ForeignKey("agent_proposals.id"), nullable=True)
        created_by = Column(String, nullable=False)  # "user" | "agent" | "undo"

        created_at = Column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            server_default=func.now(),
        )
