from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
try:
    from backend.api.dependencies import get_current_user
    from backend.database import get_db
    from backend.models.user import User
    from backend.models.credit import CreditTransaction
    from backend.models.ai_log import AIUseLog
    from backend.services.credit_service import get_credit_balance
except ImportError:
    from api.dependencies import get_current_user
    from database import get_db
    from models.user import User
    from models.credit import CreditTransaction
    from models.ai_log import AIUseLog
    from services.credit_service import get_credit_balance


router = APIRouter(prefix="/credits", tags=["credits"])

@router.get("/balance")
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    balance = await get_credit_balance(db, current_user.id)
    return {"balance": balance}


@router.get("/logs")
async def get_ai_use_logs(
    limit: int = Query(default=50, ge=1, le=100),
    project_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(AIUseLog)
        .where(AIUseLog.user_id == current_user.id)
    )
    if project_id:
        query = query.where(AIUseLog.project_id == project_id)

    query = query.order_by(desc(AIUseLog.created_at)).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "agent_name": log.agent_name,
            "tokens_used": log.tokens_used or 0,
            "credits_charged": log.credits_charged or 0,
            "duration_ms": log.duration_ms,
            "project_id": log.project_id,
            "input_summary": log.input_summary,
            "output_summary": log.output_summary,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.get("/transactions")
async def get_credit_transactions(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(CreditTransaction)
        .where(CreditTransaction.user_id == current_user.id)
        .order_by(desc(CreditTransaction.created_at))
        .limit(limit)
    )
    result = await db.execute(query)
    transactions = result.scalars().all()

    return [
        {
            "id": txn.id,
            "type": txn.type,
            "amount": txn.amount,
            "balance_after": txn.balance_after,
            "description": txn.description,
            "created_at": txn.created_at.isoformat() if txn.created_at else None,
        }
        for txn in transactions
    ]