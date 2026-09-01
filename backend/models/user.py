import sys
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

try:
    from backend.database import Base
except ImportError:
    from database import Base

import uuid

if "backend.models.user" in sys.modules and __name__ == "models.user":
    User = sys.modules["backend.models.user"].User
elif "models.user" in sys.modules and __name__ == "backend.models.user":
    User = sys.modules["models.user"].User
else:
    class User(Base):
        __tablename__ = "users"
        __table_args__ = {"extend_existing": True}

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

