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

if "backend.models.agent_job_stage" in sys.modules and __name__ == "models.agent_job_stage":
    AgentJobStage = sys.modules["backend.models.agent_job_stage"].AgentJobStage
elif "models.agent_job_stage" in sys.modules and __name__ == "backend.models.agent_job_stage":
    AgentJobStage = sys.modules["models.agent_job_stage"].AgentJobStage
else:
    class AgentJobStage(Base):
        """Individual execution stage within an AgentJob.

        Stage types:
            inspect_context, build_outline, research, extract_evidence,
            compose, validate, build_proposal
        """
        __tablename__ = "agent_job_stages"
        __table_args__ = {"extend_existing": True}

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        job_id = Column(String, ForeignKey("agent_jobs.id"), nullable=False, index=True)

        stage_type = Column(String, nullable=False)
        order = Column(Integer, nullable=False)
        status = Column(String, nullable=False, default="pending")
        # "pending" | "running" | "completed" | "failed" | "skipped"

        input_ref = Column(JSON, nullable=True)
        output_ref = Column(JSON, nullable=True)
        depends_on = Column(JSON, nullable=True)  # List of stage IDs

        retry_count = Column(Integer, default=0)
        max_retries = Column(Integer, default=2)
        tokens_used = Column(Integer, default=0)
        credits_charged = Column(Integer, default=0)
        error = Column(Text, nullable=True)

        started_at = Column(DateTime(timezone=True), nullable=True)
        completed_at = Column(DateTime(timezone=True), nullable=True)

        job = relationship("AgentJob", back_populates="stages")
