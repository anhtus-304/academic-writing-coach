import sys
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

try:
    from backend.database import Base
except ImportError:
    from database import Base

if "backend.models.agent_job" in sys.modules and __name__ == "models.agent_job":
    AgentJob = sys.modules["backend.models.agent_job"].AgentJob
elif "models.agent_job" in sys.modules and __name__ == "backend.models.agent_job":
    AgentJob = sys.modules["models.agent_job"].AgentJob
else:
    class AgentJob(Base):
        """Tracks every agent job request from user (ask or auto mode).

        Status lifecycle:
            queued -> running -> awaiting_approval -> applying -> completed
                  |-> needs_input (missing context/credit)
                  |-> failed
                  |-> cancelled
        """
        __tablename__ = "agent_jobs"
        __table_args__ = {"extend_existing": True}

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

        user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
        project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)

        mode = Column(String, nullable=False)  # "ask" | "auto"
        prompt = Column(Text, nullable=False)
        prompt_summary = Column(String(500), nullable=True)

        status = Column(String, nullable=False, default="queued")
        # "queued" | "running" | "needs_input" | "awaiting_approval"
        # | "applying" | "completed" | "failed" | "cancelled"

        plan = Column(JSON, nullable=True)  # Planner structured output
        context_snapshot = Column(JSON, nullable=True)  # Frozen input state
        result = Column(JSON, nullable=True)  # Final output / answer

        idempotency_key = Column(String, nullable=True, unique=True, index=True)
        estimated_credits = Column(Integer, default=0)
        actual_credits = Column(Integer, default=0)
        error = Column(Text, nullable=True)

        created_at = Column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            server_default=func.now(),
        )
        started_at = Column(DateTime(timezone=True), nullable=True)
        completed_at = Column(DateTime(timezone=True), nullable=True)

        # Relationships
        stages = relationship(
            "AgentJobStage",
            back_populates="job",
            cascade="all, delete-orphan",
            order_by="AgentJobStage.order",
            lazy="selectin",
        )
        proposals = relationship(
            "AgentProposal",
            back_populates="job",
            cascade="all, delete-orphan",
            lazy="selectin",
        )
