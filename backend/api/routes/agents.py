import time
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.api.dependencies import get_current_user
    from backend.database import get_db
    from backend.models.user import User
    from backend.services.credit_service import deduct_credits
    from backend.services.llm_service import llm_service
    from backend.services.ai_use_logger import ai_use_logger
except ImportError:
    from api.dependencies import get_current_user
    from database import get_db
    from models.user import User
    from services.credit_service import deduct_credits
    from services.llm_service import llm_service
    from services.ai_use_logger import ai_use_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])

ACADEMIC_COACH_SYSTEM_PROMPT = """Bạn là Trợ lý Học thuật Đa tác nhân (AI Academic Writing Coach) chuyên nghiệp, hỗ trợ người học nâng cao chất lượng bài viết khoa học.

NGUYÊN TẮC BẤT KHẢ XÂM PHẠM (PEDAGOGICAL GUARDRAILS):
1. HỖ TRỢ ĐỊNH HƯỚNG, KHÔNG VIẾT THAY: Bạn là Người huấn luyện (Coach), KHÔNG phải người viết hộ (Ghostwriter). Tuyệt đối KHÔNG viết toàn bộ một bài luận/chương sách khi người dùng yêu cầu 'Viết bài này cho tôi' hoặc 'Viết hộ tôi'. Thay vào đó, hãy phân tích cấu trúc, cung cấp dàn ý gợi mở, câu hỏi phản biện theo phương pháp Socratic để người học tự tư duy và tự viết.
2. CÁC TÁC VỤ:
   - "explain" (Giải thích thuật ngữ): Giải thích ngắn gọn, chuẩn xác ngữ nghĩa học thuật của đoạn trích, cung cấp bối cảnh ứng dụng thực tế.
   - "summarize" (Tóm tắt luận điểm): Trích xuất 1-2 luận điểm cốt lõi và bằng chứng trong 2-3 câu súc tích.
   - "academic_rewrite" (Viết lại học thuật): Nâng cao văn phong học thuật cho đoạn văn (loại bỏ từ ngữ cảm tính, tăng tính khách quan và liên kết logic). KÈM THEO phần giải thích ngắn lý do điều chỉnh.
   - "critique" (Phản biện luận cứ): Chỉ ra các điểm giả định ngầm, lỗ hổng logic hoặc thiếu sót dẫn chứng trong đoạn văn; gợi ý câu hỏi phản biện.
   - "custom" (Câu hỏi tùy chỉnh): Trả lời câu hỏi cụ thể của người học về đoạn văn bản với tư cách chuyên gia hướng dẫn nghiên cứu.
3. NGÔN NGỮ & ĐỊNH DẠNG: Trả lời bằng Tiếng Việt học thuật chuẩn mực, rõ ràng, định dạng Markdown đẹp mắt."""


class AskAIRequest(BaseModel):
    selected_text: str = Field(..., min_length=1)
    action: str = Field(default="explain")  # "explain", "summarize", "academic_rewrite", "critique", "custom"
    custom_prompt: Optional[str] = None
    project_id: Optional[str] = None


class AskAIResponse(BaseModel):
    action: str
    selected_text: str
    response: str
    tokens_used: int
    credits_charged: int


@router.post("/ask", response_model=AskAIResponse)
async def ask_agent(
    body: AskAIRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.selected_text.strip():
        raise HTTPException(status_code=400, detail="Văn bản được chọn không được để trống")

    # 1. Deduct 1 credit
    credit_deducted = await deduct_credits(
        db=db,
        user=current_user,
        amount=1,
        description=f"Hỏi AI Assistant ({body.action})",
    )
    if not credit_deducted:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Số dư không đủ (Yêu cầu 1 Credit). Vui lòng nạp thêm credit để tiếp tục sử dụng trợ lý AI.",
        )

    # 2. Build User Prompt
    action_prompts = {
        "explain": f"Hãy giải thích cặn kẽ ý nghĩa học thuật và các khái niệm then chốt trong đoạn trích sau:\n\n\"{body.selected_text}\"",
        "summarize": f"Hãy tóm tắt luận điểm chính và bằng chứng trong đoạn trích sau một cách cô đọng:\n\n\"{body.selected_text}\"",
        "academic_rewrite": f"Hãy viết lại đoạn văn sau theo chuẩn văn phong học thuật (trung tính, khách quan, súc tích) và giải thích ngắn các cải tiến:\n\n\"{body.selected_text}\"",
        "critique": f"Hãy phân tích phản biện đoạn văn sau (chỉ ra giả định ngầm, điểm yếu logic, gợi ý hoàn thiện dẫn chứng):\n\n\"{body.selected_text}\"",
        "custom": f"Đoạn văn trích dẫn:\n\"{body.selected_text}\"\n\nYêu cầu cụ thể từ người học:\n{body.custom_prompt or 'Phân tích và cho ý kiến chuyên gia về đoạn văn này.'}",
    }

    user_prompt = action_prompts.get(body.action, action_prompts["explain"])

    start_time = time.time()
    try:
        response_text, usage = await llm_service.generate_text_with_usage(
            system_prompt=ACADEMIC_COACH_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.4,
        )
    except Exception as exc:
        logger.error("LLM Assistant call failed: %s", exc)
        # Fallback response for offline or API errors
        response_text = (
            f"### Phân tích học thuật\n\n"
            f"**Đoạn trích:** *\"{body.selected_text}\"*\n\n"
            f"- **Luận điểm:** Đoạn văn bản thể hiện một ý tưởng nghiên cứu cần được hỗ trợ thêm bằng dữ liệu định lượng hoặc tài liệu tham khảo.\n"
            f"- **Gợi ý viết học thuật:** Hãy sử dụng các từ nối logic (Ví dụ: *Hơn nữa, Trái lại, Cụ thể là*) và trích dẫn nguồn uy tín để tăng độ tin cậy.\n"
            f"- **Lưu ý:** Vui lòng kiểm tra lại cấu hình OpenRouter API key để nhận phản hồi phân tích thời gian thực từ AI."
        )
        usage = {"total_tokens": 150}

    duration_ms = int((time.time() - start_time) * 1000)
    tokens_used = usage.get("total_tokens", 0)

    # 3. Log AI usage
    try:
        await ai_use_logger.log_ai_usage(
            agent_name="AIAssistant",
            tokens_used=tokens_used,
            user_id=current_user.id,
            project_id=body.project_id,
            input_summary={"action": body.action, "text_len": len(body.selected_text)},
            output_summary={"response_len": len(response_text)},
            credits_charged=1,
            duration_ms=duration_ms,
            db=db,
        )
    except Exception as exc:
        logger.warning("Failed to log AI assistant usage: %s", exc)

    return AskAIResponse(
        action=body.action,
        selected_text=body.selected_text,
        response=response_text,
        tokens_used=tokens_used,
        credits_charged=1,
    )
