from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User

async def get_credit_balance(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(select(User.credit_balance).where(User.id == user_id))
    return result.scalar_one_or_none() or 0