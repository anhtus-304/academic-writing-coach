from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_current_user
from database import get_db
from models.user import User
from services.credit_service import get_credit_balance

router = APIRouter(prefix="/credits", tags=["credits"])

@router.get("/balance")
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    balance = await get_credit_balance(db, current_user.id)
    return {"balance": balance}