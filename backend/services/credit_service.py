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


async def preauthorize_auto_mode(
    db: AsyncSession,
    user: User,
    estimated_cost: int,
) -> bool:
    """Checks whether user has enough credits for the full pipeline run."""
    current_balance = user.credit_balance or 0
    return current_balance >= estimated_cost


async def deduct_checkpoint(
    db: AsyncSession,
    user: User,
    checkpoint_name: str,
    cost: int,
) -> bool:
    """Deducts credits for an individual pipeline checkpoint stage."""
    return await deduct_credits(
        db=db,
        user=user,
        amount=cost,
        description=f"Auto Mode Checkpoint: {checkpoint_name}",
    )


async def refund_unspent(
    db: AsyncSession,
    user: User,
    refund_amount: int,
    reason: str = "",
) -> bool:
    """Refunds unspent credits (e.g. pipeline stopped early or failed)."""
    if refund_amount <= 0:
        return True
    user.credit_balance = (user.credit_balance or 0) + refund_amount
    txn = CreditTransaction(
        user_id=user.id,
        type="bonus",
        amount=refund_amount,
        balance_after=user.credit_balance,
        description=f"Refund: {reason}" if reason else "Pipeline unspent refund",
    )
    db.add(txn)
    await db.flush()
    return True