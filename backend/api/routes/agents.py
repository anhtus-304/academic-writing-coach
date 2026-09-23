import time
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

try:
    from backend.api.dependencies import get_current_user
    from backend.database import get_db
    from backend.models.user import User
    from backend.models.selected_paper import SelectedPaper
    from backend.models.cached_paper import CachedPaper
    from backend.services.credit_service import (
        deduct_credits,
        preauthorize_auto_mode,
        deduct_checkpoint,
        refund_unspent,
        get_credit_balance,
    )
    from backend.services.llm_service import llm_service
    from backend.services.ai_use_logger import ai_use_logger
    from backend.services import project_service
    from backend.config import settings
    from backend.agents.graph import (
        AgentState,
        outline_node,
        literature_node,
        citation_node,
        run_academic_pipeline,
        get_pipeline_state,
        update_pipeline_state,
    )
except ImportError:
    from api.dependencies import get_current_user
    from database import get_db
    from models.user import User
    from models.selected_paper import SelectedPaper
    from models.cached_paper import CachedPaper
    from services.credit_service import (
        deduct_credits,
        preauthorize_auto_mode,
        deduct_checkpoint,
        refund_unspent,
        get_credit_balance,
    )
    from services.llm_service import llm_service
    from services.ai_use_logger import ai_use_logger
    import services.project_service as project_service
    from config import settings
    from agents.graph import (
        AgentState,
        outline_node,
        literature_node,
        citation_node,
        run_academic_pipeline,
        get_pipeline_state,
        update_pipeline_state,
    )

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


# =====================================================================
# Mode Auto (Human-in-the-Loop Multi-Agent Pipeline)
# =====================================================================

class StageEstimateItem(BaseModel):
    name: str
    cost: int
    skip_available: bool
    description: str


class PipelineEstimateRequest(BaseModel):
    project_id: Optional[str] = None
    stages: Optional[List[str]] = None
    skip_existing_outline: bool = True


class PipelineEstimateResponse(BaseModel):
    estimated_cost: int
    user_balance: int
    sufficient_balance: bool
    disclaimer_required: bool
    stages: List[StageEstimateItem]


class PipelineRunRequest(BaseModel):
    project_id: Optional[str] = None
    topic: Optional[str] = None
    document_type: Optional[str] = "tieu_luan"
    field: Optional[str] = None
    citation_style: Optional[str] = "apa7"
    target_length: Optional[str] = None
    template_id: Optional[str] = None
    user_requirements: Optional[str] = None
    draft_content: Optional[str] = None
    disclaimer_accepted: bool = False
    stages: Optional[List[str]] = None


class PipelineRunResponse(BaseModel):
    project_id: str
    status: str
    completed_stages: List[str]
    total_credits_charged: int
    user_balance_after: int
    outline: Optional[Dict[str, Any]] = None
    literature_review: Optional[Dict[str, Any]] = None
    citation_report: Optional[Dict[str, Any]] = None
    suggestions: List[Dict[str, Any]] = []
    error: Optional[str] = None


class PipelineStateResponse(BaseModel):
    project_id: str
    status: str
    current_step: Optional[str] = None
    outline: Optional[Dict[str, Any]] = None
    literature_review: Optional[Dict[str, Any]] = None
    citation_report: Optional[Dict[str, Any]] = None
    suggestions: List[Dict[str, Any]] = []
    error: Optional[str] = None


@router.post("/pipeline/estimate", response_model=PipelineEstimateResponse)
async def estimate_pipeline_cost(
    body: PipelineEstimateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.ENABLE_AGENT_AUTO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tính năng Chế độ Tự động (Auto Mode) hiện đang tạm tắt theo cấu hình hệ thống.",
        )

    has_outline = False
    if body.project_id:
        existing_outline = await project_service.get_project_outline(db, body.project_id, current_user.id)
        if existing_outline and existing_outline.chapters:
            has_outline = True

    outline_cost = 0 if (has_outline and body.skip_existing_outline) else settings.AGENT_AUTO_CHECKPOINT_COST_OUTLINE
    stages_info = [
        StageEstimateItem(
            name="outline",
            cost=outline_cost,
            skip_available=has_outline,
            description="Bảo lưu dàn ý có sẵn hoặc khởi tạo dàn ý nghiên cứu chuẩn học thuật",
        ),
        StageEstimateItem(
            name="literature",
            cost=settings.AGENT_AUTO_CHECKPOINT_COST_LITERATURE,
            skip_available=False,
            description="Tìm kiếm & tổng quan tài liệu khoa học từ Semantic Scholar/ArXiv",
        ),
        StageEstimateItem(
            name="citation",
            cost=settings.AGENT_AUTO_CHECKPOINT_COST_CITATION,
            skip_available=False,
            description="Đối soát trích dẫn, phát hiện missing claims & đề xuất trích dẫn",
        ),
    ]

    selected_stages = body.stages or ["outline", "literature", "citation"]
    total_cost = sum(s.cost for s in stages_info if s.name in selected_stages)
    raw_bal = await get_credit_balance(db, current_user.id)
    balance = raw_bal if isinstance(raw_bal, int) else (getattr(current_user, "credit_balance", 0) or 0)

    return PipelineEstimateResponse(
        estimated_cost=total_cost,
        user_balance=balance,
        sufficient_balance=balance >= total_cost,
        disclaimer_required=settings.AGENT_AUTO_MODE_DISCLAIMER_REQUIRED,
        stages=stages_info,
    )


@router.post("/pipeline/run", response_model=PipelineRunResponse)
async def run_pipeline_auto_mode(
    body: PipelineRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.ENABLE_AGENT_AUTO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tính năng Chế độ Tự động (Auto Mode) hiện đang tạm tắt theo cấu hình hệ thống.",
        )

    if settings.AGENT_AUTO_MODE_DISCLAIMER_REQUIRED and not body.disclaimer_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn cần đồng ý với Tuyên bố Liêm chính Học thuật trước khi khởi chạy chế độ Auto.",
        )

    project = None
    existing_outline_dict = None
    draft_text = body.draft_content or ""
    selected_papers_payload: List[Dict[str, Any]] = []

    if body.project_id:
        project = await project_service.get_project(db, body.project_id, current_user.id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đề tài nghiên cứu.")

        # 1. Outline
        out_rec = await project_service.get_project_outline(db, project.id, current_user.id)
        if out_rec and out_rec.chapters:
            existing_outline_dict = {"title": out_rec.title or project.topic, "sections": out_rec.chapters}

        # 2. Draft document
        if not draft_text:
            doc_rec = await project_service.get_project_document(db, project.id, current_user.id)
            if doc_rec and doc_rec.content:
                if isinstance(doc_rec.content, dict):
                    draft_text = str(doc_rec.content.get("html") or doc_rec.content.get("text") or "")
                else:
                    draft_text = str(doc_rec.content)

        # 3. Selected papers
        sel_stmt = (
            select(SelectedPaper)
            .options(selectinload(SelectedPaper.cached_paper))
            .where(SelectedPaper.project_id == project.id)
        )
        sel_res = await db.execute(sel_stmt)
        for sp in sel_res.scalars().all():
            cp = sp.cached_paper
            if not cp and sp.cached_paper_id:
                cp = await db.get(CachedPaper, sp.cached_paper_id)
            selected_papers_payload.append({
                "id": sp.id,
                "cached_paper_id": sp.cached_paper_id,
                "title": cp.title if cp else "Tài liệu",
                "authors": cp.authors if cp else [],
                "year": cp.year if cp else (cp.publication_year if cp else 2024),
                "venue": cp.source if cp else None,
                "doi": cp.doi if cp else None,
                "url": cp.url if cp else None,
            })

    target_stages = body.stages or ["outline", "literature", "citation"]

    # Calculate preauthorization estimate
    cost_outline = 0 if (existing_outline_dict and "outline" in target_stages) else settings.AGENT_AUTO_CHECKPOINT_COST_OUTLINE
    cost_literature = settings.AGENT_AUTO_CHECKPOINT_COST_LITERATURE if "literature" in target_stages else 0
    cost_citation = settings.AGENT_AUTO_CHECKPOINT_COST_CITATION if "citation" in target_stages else 0
    total_estimated = (cost_outline if "outline" in target_stages else 0) + cost_literature + cost_citation

    # Check preauthorization
    authorized = await preauthorize_auto_mode(db, current_user, total_estimated)
    if not authorized:
        raw_bal = await get_credit_balance(db, current_user.id)
        balance = raw_bal if isinstance(raw_bal, int) else (getattr(current_user, "credit_balance", 0) or 0)
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Số dư không đủ để chạy quy trình Auto ({total_estimated} Credits, số dư hiện tại: {balance} Credits).",
        )

    # Initialize LangGraph AgentState
    state: AgentState = {
        "project_id": body.project_id or "adhoc_project",
        "user_id": current_user.id,
        "topic": (project.topic if project else body.topic) or "Đề tài nghiên cứu",
        "document_type": (project.document_type if project else body.document_type) or "tieu_luan",
        "field": project.field if project else body.field,
        "citation_style": (project.citation_style if project else body.citation_style) or "apa7",
        "target_length": body.target_length,
        "template_id": body.template_id,
        "user_requirements": body.user_requirements or (project.additional_requirements if project else None),
        "draft_content": draft_text,
        "outline": existing_outline_dict,
        "selected_papers": selected_papers_payload,
        "suggestions": [],
        "current_step": "init",
        "status": "running",
        "messages": [],
    }

    completed_stages: List[str] = []
    total_charged = 0

    try:
        # Checkpoint 1: Outline
        if "outline" in target_stages:
            if existing_outline_dict:
                completed_stages.append("outline (preserved)")
            else:
                cost = settings.AGENT_AUTO_CHECKPOINT_COST_OUTLINE
                deducted = await deduct_checkpoint(db, current_user, "Dàn ý học thuật", cost)
                if not deducted:
                    raise HTTPException(status_code=402, detail="Số dư không đủ cho bước tạo dàn ý.")
                total_charged += cost

                out_res = await outline_node(state)
                if out_res.get("status") == "failed":
                    state["error"] = out_res.get("error")
                    state["status"] = "failed"
                    current_bal = await get_credit_balance(db, current_user.id)
                    return PipelineRunResponse(
                        project_id=state["project_id"],
                        status="failed",
                        completed_stages=completed_stages,
                        total_credits_charged=total_charged,
                        user_balance_after=current_bal,
                        error=state.get("error"),
                    )

                state["outline"] = out_res.get("outline")
                completed_stages.append("outline")

                # Sync generated outline into project in DB
                if project and state.get("outline"):
                    inner = state["outline"].get("outline") or state["outline"]
                    chapters = inner.get("sections") or inner.get("chapters") or []
                    await project_service.update_project_outline(
                        db=db,
                        project_id=project.id,
                        user_id=current_user.id,
                        chapters_data=chapters,
                        suggestions_data=state["outline"].get("suggestions"),
                    )

                await ai_use_logger.log_ai_usage(
                    agent_name="OutlineAgent(Auto)",
                    tokens_used=600,
                    user_id=current_user.id,
                    project_id=body.project_id,
                    input_summary={"topic": state["topic"]},
                    output_summary={"status": "completed"},
                    credits_charged=cost,
                    duration_ms=1000,
                    db=db,
                )

        # Checkpoint 2: Literature
        if "literature" in target_stages:
            cost = settings.AGENT_AUTO_CHECKPOINT_COST_LITERATURE
            deducted = await deduct_checkpoint(db, current_user, "Tổng quan tài liệu nghiên cứu", cost)
            if not deducted:
                raise HTTPException(status_code=402, detail="Số dư không đủ cho bước tìm kiếm tài liệu.")
            total_charged += cost

            lit_res = await literature_node(state)
            if lit_res.get("status") == "failed":
                state["error"] = lit_res.get("error")
                state["status"] = "failed"
                current_bal = await get_credit_balance(db, current_user.id)
                return PipelineRunResponse(
                    project_id=state["project_id"],
                    status="failed",
                    completed_stages=completed_stages,
                    total_credits_charged=total_charged,
                    user_balance_after=current_bal,
                    outline=state.get("outline"),
                    error=state.get("error"),
                )

            state["literature_results"] = lit_res.get("literature_results")
            state["literature_review"] = lit_res.get("literature_review")
            state["selected_papers"] = lit_res.get("selected_papers")
            state["suggestions"] = lit_res.get("suggestions", [])
            completed_stages.append("literature")

            await ai_use_logger.log_ai_usage(
                agent_name="LiteratureAgent(Auto)",
                tokens_used=1000,
                user_id=current_user.id,
                project_id=body.project_id,
                input_summary={"topic": state["topic"]},
                output_summary={"papers": len(state.get("selected_papers") or [])},
                credits_charged=cost,
                duration_ms=1500,
                db=db,
            )

        # Checkpoint 3: Citation
        if "citation" in target_stages:
            cost = settings.AGENT_AUTO_CHECKPOINT_COST_CITATION
            deducted = await deduct_checkpoint(db, current_user, "Kiểm định trích dẫn & Missing Claims", cost)
            if not deducted:
                raise HTTPException(status_code=402, detail="Số dư không đủ cho bước kiểm định trích dẫn.")
            total_charged += cost

            cite_res = await citation_node(state)
            if cite_res.get("status") == "failed":
                state["error"] = cite_res.get("error")
                state["status"] = "failed"
            else:
                state["citation_report"] = cite_res.get("citation_report")
                state["citations"] = cite_res.get("citations")
                state["suggestions"] = cite_res.get("suggestions", [])
                completed_stages.append("citation")

            await ai_use_logger.log_ai_usage(
                agent_name="CitationAgent(Auto)",
                tokens_used=700,
                user_id=current_user.id,
                project_id=body.project_id,
                input_summary={"draft_len": len(draft_text)},
                output_summary={"claims": len(state.get("citations") or [])},
                credits_charged=cost,
                duration_ms=1200,
                db=db,
            )

        state["status"] = "completed"

    except Exception as exc:
        logger.error(f"[AutoMode] Unhandled exception during pipeline run: {exc}", exc_info=True)
        unspent = total_estimated - total_charged
        if unspent > 0:
            await refund_unspent(db, current_user, unspent, reason=f"Lỗi quy trình: {str(exc)}")
        state["error"] = str(exc)
        state["status"] = "failed"

    # Save to persistent thread state
    if body.project_id:
        try:
            update_pipeline_state(body.project_id, state)
        except Exception as e:
            logger.warning(f"Could not update persistent state for thread {body.project_id}: {e}")

    raw_final = await get_credit_balance(db, current_user.id)
    final_balance = raw_final if isinstance(raw_final, int) else (getattr(current_user, "credit_balance", 0) or 0)

    return PipelineRunResponse(
        project_id=state["project_id"],
        status=state.get("status", "completed"),
        completed_stages=completed_stages,
        total_credits_charged=total_charged,
        user_balance_after=final_balance,
        outline=state.get("outline"),
        literature_review=state.get("literature_review"),
        citation_report=state.get("citation_report"),
        suggestions=state.get("suggestions") or [],
        error=state.get("error"),
    )


@router.get("/pipeline/{project_id}/state", response_model=PipelineStateResponse)
async def get_project_pipeline_state(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await project_service.get_project(db, project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đề tài.")

    state = get_pipeline_state(project_id)
    if not state:
        return PipelineStateResponse(
            project_id=project_id,
            status="idle",
            current_step="none",
            suggestions=[],
        )

    return PipelineStateResponse(
        project_id=project_id,
        status=state.get("status", "completed"),
        current_step=state.get("current_step"),
        outline=state.get("outline"),
        literature_review=state.get("literature_review"),
        citation_report=state.get("citation_report"),
        suggestions=state.get("suggestions") or [],
        error=state.get("error"),
    )
