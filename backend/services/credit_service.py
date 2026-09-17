from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
try:
    from backend.models.user import User
    from backend.models.credit import CreditTransaction
except ImportError:
    from models.user import User
    from models.credit import CreditTransaction


async def get_credit_balance(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(select(User.credit_balance).where(User.id == user_id))
    return result.scalar_one_or_none() or 0


async def deduct_credits(
    db: AsyncSession,
    user: User,
    amount: int,
    description: str = "",
) -> bool:
    """Deduct credit from user if balance allows, and log a CreditTransaction.
    Returns True if successful, False if insufficient balance.
    """
    current_balance = user.credit_balance or 0
    if current_balance < amount:
        return False

    user.credit_balance = current_balance - amount
    txn = CreditTransaction(
        user_id=user.id,
        type="usage",
        amount=-amount,
        balance_after=user.credit_balance,
        description=description,
    )
    db.add(txn)
    await db.flush()
    return True