import sys
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

try:
    from backend.database import Base
except ImportError:
    from database import Base

if "backend.models.agent_decision" in sys.modules and __name__ == "models.agent_decision":
    AgentDecision = sys.modules["backend.models.agent_decision"].AgentDecision
elif "models.agent_decision" in sys.modules and __name__ == "backend.models.agent_decision":
    AgentDecision = sys.modules["models.agent_decision"].AgentDecision
else:
    class AgentDecision(Base):
        """Records user accept/reject decisions on proposal operations.

        Supports both per-operation decisions (operation_id set) and
        whole-proposal decisions (operation_id null).
        """
        __tablename__ = "agent_decisions"
        __table_args__ = {"extend_existing": True}

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        proposal_id = Column(String, ForeignKey("agent_proposals.id"), nullable=False, index=True)
        operation_id = Column(String, nullable=True)  # null = whole-proposal decision

        decision = Column(String, nullable=False)  # "accept" | "reject"
        actor_user_id = Column(String, ForeignKey("users.id"), nullable=False)
        reason = Column(Text, nullable=True)

        created_at = Column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            server_default=func.now(),
        )

        proposal = relationship("AgentProposal", back_populates="decisions")
