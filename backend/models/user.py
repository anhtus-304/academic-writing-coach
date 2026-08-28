from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    google_id = Column(String, unique=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    credit_balance = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=func.now())

    projects = relationship("Project", back_populates="owner")
    credit_transactions = relationship("CreditTransaction", back_populates="user")
    ai_use_logs = relationship("AIUseLog", back_populates="user")