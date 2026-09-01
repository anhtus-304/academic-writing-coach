from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

try:
    from backend.database import Base
except ImportError:
    from database import Base

import uuid

class AIUseLog(Base):
    __tablename__ = "ai_use_logs"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True, index=True)
    agent_name = Column(String, nullable=False)
    input_summary = Column(JSON, nullable=True)
    output_summary = Column(JSON, nullable=True)
    tokens_used = Column(Integer, default=0)
    credits_charged = Column(Integer, default=0)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="ai_use_logs")
