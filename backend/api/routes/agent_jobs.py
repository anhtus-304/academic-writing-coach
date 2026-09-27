"""Canonical Agent Job API endpoints.

Provides the 6 endpoints defined in requirements.md §6:
  POST   /agent-jobs                                        — Create job
  GET    /agent-jobs/{job_id}                                — Get status
  POST   /agent-jobs/{job_id}/cancel                         — Cancel job
  POST   /agent-jobs/{job_id}/proposals/{proposal_id}/decisions — Decisions
  POST   /agent-jobs/{job_id}/apply                          — Apply proposal
  POST   /agent-jobs/{job_id}/undo                           — Undo proposal
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

try:
    from backend.api.dependencies import get_current_user
    from backend.database import get_db
    from backend.models.user import User
    from backend.models.agent_job import AgentJob
    from backend.models.agent_job_stage import AgentJobStage
    from backend.models.agent_proposal import AgentProposal
    from backend.schemas.agent_job_schemas import (
        CreateJobRequest,
        CreateJobResponse,
        GetJobResponse,
        StageProgressItem,
        ProposalData,
        ProposalOperation,
        CancelJobResponse,
        ProposalDecisionRequest,
        ProposalDecisionResponse,
        ApplyProposalRequest,
        ApplyProposalResponse,
        UndoRequest,
        UndoResponse,
    )
    from backend.services.planner_service import planner_service
    from backend.services.orchestrator_service import orchestrator_service
    from backend.services.proposal_service import proposal_service
    from backend.services.credit_service import (
        preauthorize_auto_mode,
        get_credit_balance,
    )
    from backend.services.llm_service import llm_service
    from backend.services.ai_use_logger import ai_use_logger
    from backend.config import settings
    import backend.services.project_service as project_service
except ImportError:
    from api.dependencies import get_current_user
    from database import get_db
    from models.user import User
    from models.agent_job import AgentJob
    from models.agent_job_stage import AgentJobStage
    from models.agent_proposal import AgentProposal
    from schemas.agent_job_schemas import (
        CreateJobRequest,
        CreateJobResponse,
        GetJobResponse,
        StageProgressItem,
        ProposalData,
        ProposalOperation,
        CancelJobResponse,
        ProposalDecisionRequest,
        ProposalDecisionResponse,
        ApplyProposalRequest,
        ApplyProposalResponse,
        UndoRequest,
        UndoResponse,
    )
    from services.planner_service import planner_service
    from services.orchestrator_service import orchestrator_service
    from services.proposal_service import proposal_service
    from services.credit_service import (
        preauthorize_auto_mode,
        get_credit_balance,
    )
    from services.llm_service import llm_service
    from services.ai_use_logger import ai_use_logger
    from config import settings
    import services.project_service as project_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-jobs", tags=["agent-jobs"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. POST /agent-jobs — Create Job
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("", response_model=CreateJobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    body: CreateJobRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create and start a new agent job."""

    # Validate project access
    project = await project_service.get_project(db, body.project_id, current_user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đề tài nghiên cứu.",
        )

    # Idempotency check
    if body.idempotency_key:
        existing = await db.execute(
            select(AgentJob).where(AgentJob.idempotency_key == body.idempotency_key)
        )
        existing_job = existing.scalar_one_or_none()
        if existing_job:
            return CreateJobResponse(
                job_id=existing_job.id,
                status=existing_job.status,
                mode=existing_job.mode,
                estimated_credits=existing_job.estimated_credits or 0,
                plan=existing_job.plan,
            )

    # Build context for planner
    context = {
        "topic": project.topic,
        "outline": None,
        "draft_content": None,
        "selected_papers": [],
    }
    outline_rec = await project_service.get_project_outline(
        db, body.project_id, current_user.id
    )
    if outline_rec and outline_rec.chapters:
        context["outline"] = {"title": outline_rec.title, "sections": outline_rec.chapters}

    doc_rec = await project_service.get_project_document(
        db, body.project_id, current_user.id
    )
    if doc_rec and doc_rec.content:
        context["draft_content"] = (
            doc_rec.content.get("html", "") if isinstance(doc_rec.content, dict) else str(doc_rec.content)
        )

    # Run planner
    plan = await planner_service.create_plan(
        mode=body.mode,
        prompt=body.prompt,
        context=context,
    )

    estimated_credits = plan.get("estimated_credits", 0)

    # Check disclaimer for auto mode
    if body.mode == "auto":
        if settings.AGENT_AUTO_MODE_DISCLAIMER_REQUIRED and not body.disclaimer_accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bạn cần đồng ý với Tuyên bố Liêm chính Học thuật trước khi khởi chạy Auto.",
            )

        # Preauthorize credits
        authorized = await preauthorize_auto_mode(db, current_user, estimated_credits)
        if not authorized:
            balance = await get_credit_balance(db, current_user.id)
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Số dư không đủ ({estimated_credits} Credits, hiện có: {balance} Credits).",
            )

    # Create job record
    job = AgentJob(
        user_id=current_user.id,
        project_id=body.project_id,
        mode=body.mode,
        prompt=body.prompt,
        prompt_summary=body.prompt[:200] if body.prompt else None,
        status="queued",
        plan=plan.get("stages"),
        estimated_credits=estimated_credits,
        idempotency_key=body.idempotency_key,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Create stage records for auto mode
    if body.mode == "auto" and plan.get("stages"):
        for i, stage_plan in enumerate(plan["stages"]):
            stage = AgentJobStage(
                job_id=job.id,
                stage_type=stage_plan.get("stage_type", "inspect_context"),
                order=i,
                status="pending",
                depends_on=stage_plan.get("depends_on", []),
            )
            db.add(stage)
        await db.commit()

    # Execute job
    if body.mode == "ask":
        # Ask mode: execute inline (synchronous)
        result = await _execute_ask_inline(db, job, current_user, body)
        return CreateJobResponse(
            job_id=job.id,
            status=job.status,
            mode=job.mode,
            estimated_credits=estimated_credits,
            plan=plan.get("stages"),
            result=result,
        )
    else:
        # Auto mode: execute in background with isolated session & task registry
        background_tasks.add_task(
            orchestrator_service.start_job, job.id, current_user.id
        )
        return CreateJobResponse(
            job_id=job.id,
            status="queued",
            mode=job.mode,
            estimated_credits=estimated_credits,
            plan=plan.get("stages"),
        )


async def _execute_ask_inline(
    db: AsyncSession,
    job: AgentJob,
    user: User,
    body: CreateJobRequest,
) -> dict:
    """Execute ask-mode job inline and return result."""
    import time

    job.status = "running"
    await db.commit()

    text_to_analyze = body.selection or body.prompt
    action = body.requested_action or "custom"

    SYSTEM_PROMPT = (
        "Bạn là Trợ lý Học thuật chuyên nghiệp. "
        "Trả lời câu hỏi dựa trên ngữ cảnh project và tài liệu đã có. "
        "Trả lời bằng Tiếng Việt học thuật, format Markdown."
    )

    start = time.time()
    try:
        from backend.services.credit_service import deduct_credits
    except ImportError:
        from services.credit_service import deduct_credits

    deducted = await deduct_credits(db, user, 1, f"Ask Agent ({action})")
    if not deducted:
        job.status = "failed"
        job.error = "Số dư không đủ"
        await db.commit()
        return {"error": "Số dư không đủ"}

    try:
        response_text, usage = await llm_service.generate_text_with_usage(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=text_to_analyze,
            temperature=0.4,
        )
    except Exception as e:
        response_text = f"Lỗi khi gọi AI: {e}"
        usage = {"total_tokens": 0}

    duration_ms = int((time.time() - start) * 1000)

    job.status = "completed"
    job.actual_credits = 1
    job.result = {"response": response_text, "tokens": usage.get("total_tokens", 0)}
    await db.commit()

    try:
        await ai_use_logger.log_ai_usage(
            agent_name="AskAgent",
            tokens_used=usage.get("total_tokens", 0),
            user_id=user.id,
            project_id=body.project_id,
            input_summary={"action": action, "text_len": len(text_to_analyze)},
            output_summary={"response_len": len(response_text)},
            credits_charged=1,
            duration_ms=duration_ms,
            db=db,
        )
    except Exception as e:
        logger.warning("Failed to log ask usage: %s", e)

    return {"response": response_text, "tokens": usage.get("total_tokens", 0)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _build_get_job_response(job: AgentJob) -> GetJobResponse:
    """Helper to convert AgentJob ORM to GetJobResponse schema."""
    stages_progress = [
        StageProgressItem(
            stage_id=s.id,
            stage_type=s.stage_type,
            order=s.order,
            status=s.status,
            tokens_used=s.tokens_used or 0,
            credits_charged=s.credits_charged or 0,
            error=s.error,
            started_at=s.started_at.isoformat() if s.started_at else None,
            completed_at=s.completed_at.isoformat() if s.completed_at else None,
        )
        for s in sorted(job.stages, key=lambda x: x.order)
    ]

    proposals_data = [
        ProposalData(
            proposal_id=p.id,
            base_version=p.base_version,
            base_hash=p.base_hash,
            target_type=p.target_type,
            target_section_id=p.target_section_id,
            operations=[
                ProposalOperation(**op) for op in (p.operations or [])
            ],
            warnings=p.warnings or [],
            status=p.status,
            tracked_html=getattr(p, "tracked_html", None),
            summary=getattr(p, "summary", None),
        )
        for p in job.proposals
    ]

    return GetJobResponse(
        job_id=job.id,
        project_id=job.project_id,
        mode=job.mode,
        status=job.status,
        prompt_summary=job.prompt_summary,
        plan=job.plan,
        stages=stages_progress,
        proposals=proposals_data,
        estimated_credits=job.estimated_credits or 0,
        actual_credits=job.actual_credits or 0,
        result=job.result,
        error=job.error,
        created_at=job.created_at.isoformat() if job.created_at else None,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2a. GET /agent-jobs/active — Get Latest Active Job for Project
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/active", response_model=Optional[GetJobResponse])
async def get_active_job(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Find the most recent running or unreviewed job for this project."""
    stmt = (
        select(AgentJob)
        .options(
            selectinload(AgentJob.stages),
            selectinload(AgentJob.proposals),
        )
        .where(
            AgentJob.project_id == project_id,
            AgentJob.user_id == current_user.id,
            AgentJob.status.in_(["queued", "running", "awaiting_approval"]),
        )
        .order_by(AgentJob.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        return None
    return _build_get_job_response(job)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2b. GET /agent-jobs/{job_id} — Get Job Status
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/{job_id}", response_model=GetJobResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current status, plan, stage progress, and proposals for a job."""

    stmt = (
        select(AgentJob)
        .options(
            selectinload(AgentJob.stages),
            selectinload(AgentJob.proposals),
        )
        .where(AgentJob.id == job_id, AgentJob.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job không tồn tại.")

    return _build_get_job_response(job)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. POST /agent-jobs/{job_id}/cancel — Cancel Job
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/{job_id}/cancel", response_model=CancelJobResponse)
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running or queued job."""

    job = await db.get(AgentJob, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job không tồn tại.")

    try:
        result = await orchestrator_service.cancel_job(db, job_id, current_user)
        return CancelJobResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. POST /agent-jobs/{job_id}/proposals/{proposal_id}/decisions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post(
    "/{job_id}/proposals/{proposal_id}/decisions",
    response_model=ProposalDecisionResponse,
)
async def submit_decisions(
    job_id: str,
    proposal_id: str,
    body: ProposalDecisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept or reject individual operations in a proposal."""

    # Verify ownership
    job = await db.get(AgentJob, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job không tồn tại.")

    proposal = await db.get(AgentProposal, proposal_id)
    if not proposal or proposal.job_id != job_id:
        raise HTTPException(status_code=404, detail="Proposal không tồn tại.")

    if proposal.status in ("applied", "conflict"):
        raise HTTPException(
            status_code=400,
            detail=f"Proposal đã ở trạng thái {proposal.status}, không thể thay đổi.",
        )

    try:
        decisions_data = [d.model_dump() for d in body.decisions]
        updated = await proposal_service.record_decisions(
            db=db,
            proposal_id=proposal_id,
            user_id=current_user.id,
            decisions=decisions_data,
            accept_all=body.accept_all,
            reject_all=body.reject_all,
        )

        return ProposalDecisionResponse(
            proposal_id=updated.id,
            status=updated.status,
            operations=[
                ProposalOperation(**op) for op in (updated.operations or [])
            ],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. POST /agent-jobs/{job_id}/apply — Apply Proposal
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/{job_id}/apply", response_model=ApplyProposalResponse)
async def apply_proposal(
    job_id: str,
    body: ApplyProposalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply accepted operations to the document."""

    job = await db.get(AgentJob, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job không tồn tại.")

    try:
        result = await proposal_service.apply_proposal(
            db=db,
            project_id=job.project_id,
            proposal_id=body.proposal_id,
            accepted_operation_ids=body.accepted_operation_ids,
            base_version=body.base_version,
            base_hash=body.base_hash,
            action=body.action or "accept_all",
            target_operation_id=body.target_operation_id,
        )

        if result["success"]:
            job.status = "completed"
            await db.commit()

        return ApplyProposalResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. POST /agent-jobs/{job_id}/undo — Undo Applied Proposal
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/{job_id}/undo", response_model=UndoResponse)
async def undo_proposal(
    job_id: str,
    body: UndoRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Undo a previously applied proposal."""

    job = await db.get(AgentJob, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job không tồn tại.")

    try:
        result = await proposal_service.undo_proposal(
            db=db,
            project_id=job.project_id,
            proposal_id=body.proposal_id,
        )
        return UndoResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
