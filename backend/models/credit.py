from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, synonym

try:
    from backend.database import Base
except ImportError:
    from database import Base

import sys
import uuid

if "backend.models.credit" in sys.modules and __name__ == "models.credit":
    CreditTransaction = sys.modules["backend.models.credit"].CreditTransaction
elif "models.credit" in sys.modules and __name__ == "backend.models.credit":
    CreditTransaction = sys.modules["models.credit"].CreditTransaction
else:
    class CreditTransaction(Base):
        __tablename__ = "credit_transactions"
        __table_args__ = {"extend_existing": True}

        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

        user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
        type = Column(Enum("purchase", "usage", "bonus", name="credit_txn_type_enum"), nullable=False)
        amount = Column(Integer, nullable=False)
        balance_after = Column(Integer, nullable=False)
        description = Column(String, nullable=True)
        payment_ref = Column(String, nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())

        transaction_type = synonym("type")

        user = relationship("User", back_populates="credit_transactions")
