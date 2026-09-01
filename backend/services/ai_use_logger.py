import math
import logging
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.database import AsyncSessionLocal
    from backend.models.ai_log import AIUseLog
except ImportError:
    from database import AsyncSessionLocal
    from models.ai_log import AIUseLog

logger = logging.getLogger(__name__)


class AIUseLogger:
    """Service responsible for logging token consumption, credit charges, and agent usage metrics."""

    @staticmethod
    def calculate_credits(tokens_used: int, rate_per_1000_tokens: float = 1.0) -> int:
        """Calculate credit charge based on token count."""
        if tokens_used <= 0:
            return 0
        credits = math.ceil((tokens_used / 1000.0) * rate_per_1000_tokens)
        return max(1, credits)

    async def log_ai_usage(
        self,
        agent_name: str,
        tokens_used: int,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        input_summary: Optional[Dict[str, Any]] = None,
        output_summary: Optional[Dict[str, Any]] = None,
        credits_charged: Optional[int] = None,
        duration_ms: Optional[int] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[AIUseLog]:
        """Logs AI usage metrics to database."""
        calculated_credits = (
            credits_charged
            if credits_charged is not None
            else self.calculate_credits(tokens_used)
        )

        effective_user_id = user_id or "system_anonymous"

        log_entry = AIUseLog(
            user_id=effective_user_id,
            project_id=project_id,
            agent_name=agent_name,
            input_summary=input_summary,
            output_summary=output_summary,
            tokens_used=tokens_used,
            credits_charged=calculated_credits,
            duration_ms=duration_ms,
        )

        logger.info(
            f"[AIUseLogger] Agent='{agent_name}', User='{effective_user_id}', "
            f"Tokens={tokens_used}, Credits={calculated_credits}, Duration={duration_ms}ms"
        )

        # If user_id is anonymous and DB constraints require a real FK, try/catch session commit
        try:
            if db is not None:
                db.add(log_entry)
                await db.flush()
                return log_entry
            else:
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        session.add(log_entry)
                    return log_entry
        except Exception as err:
            logger.warning(
                f"[AIUseLogger] Could not persist AI use log to database: {err}"
            )
            return log_entry


# Shared singleton instance
ai_use_logger = AIUseLogger()
